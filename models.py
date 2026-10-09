# """
# Data layer for Authentix.
# Tries MongoDB first (localhost:27017 / MONGO_URI env var).
# Falls back automatically to a local JSON document store so the
# app runs out-of-the-box even without a MongoDB server installed.
# """

# import os
# import json
# import threading
# from datetime import datetime, timezone

# DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
# os.makedirs(DATA_DIR, exist_ok=True)
# PRODUCTS_FILE = os.path.join(DATA_DIR, "products.json")
# SCANS_FILE = os.path.join(DATA_DIR, "scans.json")

# _lock = threading.Lock()


# def _now():
#     return datetime.now(timezone.utc).isoformat()


# # ---------------------------------------------------------------------
# # JSON fallback store
# # ---------------------------------------------------------------------
# class _JSONCollection:
#     def __init__(self, path):
#         self.path = path
#         if not os.path.exists(path):
#             with open(path, "w") as f:
#                 json.dump([], f)

#     def _read(self):
#         with open(self.path, "r") as f:
#             return json.load(f)

#     def _write(self, docs):
#         with open(self.path, "w") as f:
#             json.dump(docs, f, indent=2, default=str)

#     def insert_one(self, doc):
#         with _lock:
#             docs = self._read()
#             docs.append(doc)
#             self._write(docs)
#         return doc

#     def find_one(self, query):
#         docs = self._read()
#         for d in docs:
#             if all(d.get(k) == v for k, v in query.items()):
#                 return d
#         return None

#     def find(self, query=None):
#         docs = self._read()
#         if not query:
#             return docs
#         return [d for d in docs if all(d.get(k) == v for k, v in query.items())]

#     def update_one(self, query, update):
#         with _lock:
#             docs = self._read()
#             for d in docs:
#                 if all(d.get(k) == v for k, v in query.items()):
#                     d.update(update.get("$set", {}))
#                     break
#             self._write(docs)

#     def count(self):
#         return len(self._read())


# class Database:
#     """Unified interface: mongo collections if available, else JSON files."""

#     def __init__(self):
#         self.mode = "json"
#         self.products = _JSONCollection(PRODUCTS_FILE)
#         self.scans = _JSONCollection(SCANS_FILE)
#         self._try_mongo()

#     def _try_mongo(self):
#         try:
#             from pymongo import MongoClient
#             uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
#             client = MongoClient(uri, serverSelectionTimeoutMS=800)
#             client.admin.command("ping")
#             db = client["authentix"]
#             self.products = db["products"]
#             self.scans = db["scans"]
#             self.mode = "mongodb"
#         except Exception:
#             # Silent fallback — JSON store already initialised above
#             self.mode = "json"


# db = Database()


# def new_product_doc(product_id, name, manufacturer, description, original_image_path,
#                      image_hash, block_index, tx_hash):
#     return {
#         "product_id": product_id,
#         "name": name,
#         "manufacturer": manufacturer,
#         "description": description,
#         "original_image_path": original_image_path,
#         "image_hash": image_hash,
#         "block_index": block_index,
#         "tx_hash": tx_hash,
#         "created_at": _now(),
#     }


# def new_scan_doc(product_id, similarity, verdict, captured_image_path):
#     return {
#         "product_id": product_id,
#         "similarity": similarity,
#         "verdict": verdict,
#         "captured_image_path": captured_image_path,
#         "scanned_at": _now(),
#     }



"""
Authentix database layer.

Primary storage:
    MongoDB Atlas using MONGO_URI and MONGO_DB_NAME.

Fallback storage:
    JSON files when MongoDB is unavailable.

Note:
    Vercel's /tmp directory is temporary. JSON fallback data is
    not permanent and may not be shared between serverless instances.
"""

import os
import json
import threading
from datetime import datetime, timezone


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if os.environ.get("VERCEL"):
    DATA_DIR = "/tmp/authentix_data"
else:
    DATA_DIR = os.path.join(BASE_DIR, "data")

os.makedirs(DATA_DIR, exist_ok=True)

PRODUCTS_FILE = os.path.join(DATA_DIR, "products.json")
SCANS_FILE = os.path.join(DATA_DIR, "scans.json")

_lock = threading.Lock()


def _now():
    """Return the current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------
# JSON fallback collection
# ---------------------------------------------------------------------

class _JSONCollection:
    """Small JSON-based fallback with basic MongoDB-like operations."""

    def __init__(self, filepath):
        self.filepath = filepath
        self._ensure_file()

    def _ensure_file(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)

        if not os.path.exists(self.filepath):
            with open(self.filepath, "w", encoding="utf-8") as file:
                json.dump([], file)

    def _read(self):
        self._ensure_file()

        try:
            with open(self.filepath, "r", encoding="utf-8") as file:
                data = json.load(file)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def _write(self, documents):
        temporary_file = self.filepath + ".tmp"

        with open(temporary_file, "w", encoding="utf-8") as file:
            json.dump(documents, file, indent=2, default=str)

        os.replace(temporary_file, self.filepath)

    @staticmethod
    def _matches(document, query):
        query = query or {}

        for key, expected in query.items():
            if document.get(key) != expected:
                return False

        return True

    def insert_one(self, document):
        new_document = dict(document)

        with _lock:
            documents = self._read()

            if "_id" not in new_document:
                new_document["_id"] = (
                    f"json_{datetime.now(timezone.utc).timestamp()}"
                )

            documents.append(new_document)
            self._write(documents)

        return {"inserted_id": new_document["_id"]}

    def find_one(self, query=None):
        with _lock:
            documents = self._read()

            for document in documents:
                if self._matches(document, query):
                    return dict(document)

        return None

    def find(self, query=None):
        with _lock:
            documents = self._read()

            return [
                dict(document)
                for document in documents
                if self._matches(document, query)
            ]

    def update_one(self, query, update, upsert=False):
        with _lock:
            documents = self._read()

            for document in documents:
                if self._matches(document, query):
                    if "$set" in update:
                        document.update(update["$set"])
                    self._write(documents)
                    return {"matched_count": 1, "modified_count": 1}

            if upsert:
                new_document = dict(query or {})
                new_document.update(update.get("$set", {}))

                if "_id" not in new_document:
                    new_document["_id"] = (
                        f"json_{datetime.now(timezone.utc).timestamp()}"
                    )

                documents.append(new_document)
                self._write(documents)

                return {"matched_count": 0, "upserted_id": new_document["_id"]}

        return {"matched_count": 0, "modified_count": 0}

    def count_documents(self, query=None):
        with _lock:
            documents = self._read()

            return sum(
                1 for document in documents
                if self._matches(document, query)
            )


# ---------------------------------------------------------------------
# Database manager
# ---------------------------------------------------------------------

class Database:
    """Use MongoDB Atlas when configured; otherwise use JSON fallback."""

    def __init__(self):
        self.mode = "json"
        self.connection_error = None
        self.client = None

        # Initialize fallback collections first.
        self.products = _JSONCollection(PRODUCTS_FILE)
        self.scans = _JSONCollection(SCANS_FILE)

        self._try_mongo()

    def _try_mongo(self):
        uri = os.environ.get("MONGO_URI", "").strip()

        if not uri:
            self.connection_error = "MONGO_URI is not configured"
            print("MongoDB connection failed:", self.connection_error)
            return

        client = None

        try:
            from pymongo import MongoClient

            client = MongoClient(
                uri,
                serverSelectionTimeoutMS=8000,
                connectTimeoutMS=8000,
            )

            # Force a connection attempt and validate connectivity.
            client.admin.command("ping")

            db_name = os.environ.get(
                "MONGO_DB_NAME",
                "authentix",
            ).strip()

            if not db_name:
                db_name = "authentix"

            database = client[db_name]

            # Switch collections only after the connection succeeds.
            self.products = database["products"]
            self.scans = database["scans"]
            self.client = client
            self.mode = "mongodb"
            self.connection_error = None

            print(
                f"MongoDB Atlas connected successfully. Database: {db_name}"
            )

        except Exception as error:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass

            self.client = None
            self.mode = "json"
            self.connection_error = (
                f"{type(error).__name__}: {str(error)}"
            )

            print("MongoDB connection failed:", self.connection_error)
            print("Using JSON fallback store.")


# Create one shared database instance.
db = Database()


# ---------------------------------------------------------------------
# Product document factory
# ---------------------------------------------------------------------

def new_product_doc(
    product_id,
    name,
    manufacturer,
    description,
    original_image_path,
    image_hash,
    block_index,
    tx_hash,
):
    """Create a document for a registered product."""

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


# ---------------------------------------------------------------------
# Verification scan document factory
# ---------------------------------------------------------------------

def new_scan_doc(
    product_id,
    similarity,
    verdict,
    captured_image_path,
):
    """Create a document for a product verification scan."""

    return {
        "product_id": product_id,
        "similarity": similarity,
        "verdict": verdict,
        "captured_image_path": captured_image_path,
        "scanned_at": _now(),
    }
