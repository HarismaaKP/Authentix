"""
Blockchain layer for Authentix.

Primary path: connect to a local Ethereum node (Hardhat/Ganache) at
RPC_URL and call the deployed AuthChain smart contract (see
/blockchain/contracts/AuthChain.sol) via Web3.py.

Fallback path: if no node is reachable, product records are written
to a local, tamper-evident, SHA-256 hash-linked ledger
(data/chain.json) so the full register -> verify flow keeps working
for local demos without requiring Hardhat/Ganache to be running.
"""

import os
import json
import hashlib
import threading
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
CHAIN_FILE = os.path.join(DATA_DIR, "chain.json")
RPC_URL = os.environ.get("RPC_URL", "http://127.0.0.1:8545")
CONTRACT_ADDRESS = os.environ.get("CONTRACT_ADDRESS")

_lock = threading.Lock()


def _now():
    return datetime.now(timezone.utc).isoformat()


def _hash_block(index, product_id, image_hash, prev_hash, timestamp):
    payload = f"{index}{product_id}{image_hash}{prev_hash}{timestamp}".encode()
    return hashlib.sha256(payload).hexdigest()


class LocalLedger:
    """Deterministic hash-linked chain used when no live node is present."""

    def __init__(self):
        if not os.path.exists(CHAIN_FILE):
            genesis = {
                "index": 0,
                "product_id": "GENESIS",
                "image_hash": "0" * 64,
                "prev_hash": "0" * 64,
                "timestamp": _now(),
            }
            genesis["hash"] = _hash_block(
                genesis["index"], genesis["product_id"],
                genesis["image_hash"], genesis["prev_hash"], genesis["timestamp"]
            )
            with open(CHAIN_FILE, "w") as f:
                json.dump([genesis], f, indent=2)

    def _read(self):
        with open(CHAIN_FILE, "r") as f:
            return json.load(f)

    def _write(self, chain):
        with open(CHAIN_FILE, "w") as f:
            json.dump(chain, f, indent=2)

    def add_block(self, product_id, image_hash):
        with _lock:
            chain = self._read()
            prev = chain[-1]
            index = prev["index"] + 1
            timestamp = _now()
            block = {
                "index": index,
                "product_id": product_id,
                "image_hash": image_hash,
                "prev_hash": prev["hash"],
                "timestamp": timestamp,
            }
            block["hash"] = _hash_block(index, product_id, image_hash, prev["hash"], timestamp)
            chain.append(block)
            self._write(chain)
            tx_hash = "0xLOCAL" + block["hash"][:58]
            return index, tx_hash

    def get_block(self, product_id):
        chain = self._read()
        for b in reversed(chain):
            if b["product_id"] == product_id:
                return b
        return None

    def verify_chain_integrity(self):
        chain = self._read()
        for i in range(1, len(chain)):
            b = chain[i]
            expected = _hash_block(b["index"], b["product_id"], b["image_hash"], b["prev_hash"], b["timestamp"])
            if expected != b["hash"] or b["prev_hash"] != chain[i - 1]["hash"]:
                return False
        return True


class BlockchainClient:
    def __init__(self):
        self.mode = "local_ledger"
        self.ledger = LocalLedger()
        self.w3 = None
        self.contract = None
        self._try_web3()

    def _try_web3(self):
        try:
            from web3 import Web3
            w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 1}))
            if w3.is_connected() and CONTRACT_ADDRESS:
                abi_path = os.path.join(os.path.dirname(__file__), "blockchain", "AuthChainABI.json")
                if os.path.exists(abi_path):
                    with open(abi_path) as f:
                        abi = json.load(f)
                    self.w3 = w3
                    self.contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=abi)
                    self.mode = "web3"
        except Exception:
            self.mode = "local_ledger"

    def register_product(self, product_id, image_hash):
        """Returns (block_index_or_none, tx_hash)."""
        if self.mode == "web3" and self.contract:
            try:
                acct = self.w3.eth.accounts[0]
                tx = self.contract.functions.registerProduct(product_id, image_hash).transact({"from": acct})
                receipt = self.w3.eth.wait_for_transaction_receipt(tx)
                return receipt.blockNumber, receipt.transactionHash.hex()
            except Exception:
                pass  # fall through to local ledger
        return self.ledger.add_block(product_id, image_hash)

    def get_record(self, product_id):
        if self.mode == "web3" and self.contract:
            try:
                result = self.contract.functions.getProduct(product_id).call()
                return {"product_id": product_id, "image_hash": result[0], "block_index": None}
            except Exception:
                pass
        block = self.ledger.get_block(product_id)
        return block

    def chain_status(self):
        return {
            "mode": self.mode,
            "integrity_ok": self.ledger.verify_chain_integrity(),
            "blocks": len(self.ledger._read()),
        }


chain = BlockchainClient()



