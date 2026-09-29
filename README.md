# Authentix

Blockchain-backed product authentication and anti-counterfeit verification.

Manufacturers register a product with a reference photo. The product's
identity and image fingerprint are committed to a blockchain and a QR
code is generated. Customers scan the QR, pull the registered record,
photograph the item they're holding, and an AI region-comparison model
returns a verdict: **Authentic**, **Suspicious**, or **Counterfeit**.

## Stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, vanilla JavaScript, jsQR (camera scanning) |
| Backend | Python, Flask |
| Database | MongoDB (auto-fallback to local JSON store if no MongoDB is running) |
| Blockchain | Ethereum-compatible (Hardhat/Ganache) via Web3.py, with a local SHA-256 hash-chain fallback |
| Smart contract | Solidity (`blockchain/contracts/AuthChain.sol`) |
| QR generation | `qrcode` (Python) |
| Image processing | OpenCV (ORB region/feature matching) |
| Deep features (optional) | PyTorch + torchvision ResNet50 |

The app is designed to run standalone out of the box: if MongoDB or a
blockchain node isn't running, it transparently falls back to a local
JSON store and a tamper-evident local ledger, so the full
register → scan → verify flow always works for a demo.

## Quick start (fallback mode — no MongoDB/Hardhat required)

```bash
cd authentix
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000

- **Register a product** → fills the form, uploads a reference photo,
  and shows the generated QR code plus the ledger receipt.
- **Verify a product** → scan the QR (camera or upload), or paste a
  product ID manually, then capture/upload the product in hand for
  the AI verdict.

## Running with a real blockchain (optional)

```bash
cd blockchain
npm install
npm run node          # starts a local Hardhat chain on :8545
npm run deploy        # in a second terminal — deploys AuthChain.sol
```

The deploy script prints a `CONTRACT_ADDRESS`. Export it (and
`RPC_URL` if different) before starting Flask:

```bash
export RPC_URL=http://127.0.0.1:8545
export CONTRACT_ADDRESS=0x...
python app.py
```

The backend detects the live chain automatically and uses it instead
of the local ledger.

## Running with MongoDB (optional)

Start MongoDB locally (or set `MONGO_URI`) before `python app.py`;
the app pings it on startup and switches storage backends
automatically — no code changes needed.

## Enabling deep AI features (optional)

The base image comparison uses OpenCV ORB region matching and works
with no extra setup. Installing PyTorch + torchvision additionally
enables a ResNet50 deep-feature similarity signal that's blended into
the final score:

```bash
pip install torch torchvision
```

## Project layout

```
authentix/
├── app.py                  Flask routes (pages + API)
├── models.py                MongoDB / JSON data layer
├── blockchain_client.py     Web3 / local ledger layer
├── ai_verify.py              Region-based image comparison
├── qr_utils.py                QR generation, hashing
├── templates/                 Jinja pages
├── static/css, static/js       Styling + frontend logic
├── data/                        JSON store + local ledger (auto-created)
└── blockchain/                   Solidity contract + Hardhat project
```
