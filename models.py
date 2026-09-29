"""
Data layer for Authentix.
Tries MongoDB first (localhost:27017 / MONGO_URI env var).
Falls back automatically to a local JSON document store so the
app runs out-of-the-box even without a MongoDB server installed.
"""

import os
import json
import threading
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
PRODUCTS_FILE = os.path.join(DATA_DIR, "products.json")
SCANS_FILE = os.path.join(DATA_DIR, "scans.json")

_lock = threading.Lock()


def _now():
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------
# JSON fallback store
# ---------------------------------------------------------------------
class _JSONCollection:
    def __init__(self, path):
        self.path = path
        if not os.path.exists(path):
            with open(path, "w") as f:
                json.dump([], f)

    def _read(self):
        with open(self.path, "r") as f:
            return json.load(f)

    def _write(self, docs):
        with open(self.path, "w") as f:
            json.dump(docs, f, indent=2, default=str)

    def insert_one(self, doc):
        with _lock:
            docs = self._read()
            docs.append(doc)
            self._write(docs)
        return doc

    def find_one(self, query):
        docs = self._read()
        for d in docs:
            if all(d.get(k) == v for k, v in query.items()):
                return d
        return None

    def find(self, query=None):
        docs = self._read()
        if not query:
            return docs
        return [d for d in docs if all(d.get(k) == v for k, v in query.items())]

    def update_one(self, query, update):
        with _lock:
            docs = self._read()
            for d in docs:
                if all(d.get(k) == v for k, v in query.items()):
                    d.update(update.get("$set", {}))
                    break
            self._write(docs)

    def count(self):
        return len(self._read())


class Database:
    """Unified interface: mongo collections if available, else JSON files."""

    def __init__(self):
        self.mode = "json"
        self.products = _JSONCollection(PRODUCTS_FILE)
        self.scans = _JSONCollection(SCANS_FILE)
        self._try_mongo()

    def _try_mongo(self):
        try:
            from pymongo import MongoClient
            uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
            client = MongoClient(uri, serverSelectionTimeoutMS=800)
            client.admin.command("ping")
            db = client["authentix"]
            self.products = db["products"]
            self.scans = db["scans"]
            self.mode = "mongodb"
        except Exception:
            # Silent fallback — JSON store already initialised above
            self.mode = "json"


db = Database()


def new_product_doc(product_id, name, manufacturer, description, original_image_path,
                     image_hash, block_index, tx_hash):
    return {
        "product_id": product_id,
        "name": name,
        "manufacturer": manufacturer,
        "description": description,
        "original_image_path": original_image_path,
        "image_hash": image_hash,
        "block_index": block_index,
        "tx_hash": tx_hash,
        "created_at": _now(),
    }


def new_scan_doc(product_id, similarity, verdict, captured_image_path):
    return {
        "product_id": product_id,
        "similarity": similarity,
        "verdict": verdict,
        "captured_image_path": captured_image_path,
        "scanned_at": _now(),
    }
