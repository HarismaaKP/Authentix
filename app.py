
# import os
# import uuid
# import tempfile
# import urllib.request

# from flask import Flask, render_template, request, jsonify
# from flask_cors import CORS

# import cloudinary
# from cloudinary import uploader

# from models import db, new_product_doc, new_scan_doc
# from blockchain_client import chain
# from qr_utils import generate_product_id, generate_qr, hash_image_file
# import ai_verify


# # ---------------------------------------------------------------------
# # Configuration
# # ---------------------------------------------------------------------

# BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ALLOWED_EXT = {"png", "jpg", "jpeg", "webp"}

# app = Flask(__name__)
# CORS(app)

# # Maximum upload size: 16 MB
# app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024


# # ---------------------------------------------------------------------
# # Cloudinary configuration
# # ---------------------------------------------------------------------

# cloudinary.config(
#     cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
#     api_key=os.environ.get("CLOUDINARY_API_KEY"),
#     api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
#     secure=True,
# )


# # ---------------------------------------------------------------------
# # Helper functions
# # ---------------------------------------------------------------------

# def allowed_file(filename):
#     """Check whether the uploaded file has an allowed extension."""

#     if not filename or "." not in filename:
#         return False

#     extension = filename.rsplit(".", 1)[1].lower()
#     return extension in ALLOWED_EXT


# def save_temp_upload(file_storage, prefix):
#     """Save an uploaded image temporarily."""

#     original_filename = file_storage.filename or ""

#     if "." not in original_filename:
#         raise ValueError("The uploaded file must have an extension.")

#     extension = original_filename.rsplit(".", 1)[1].lower()

#     filename = f"{prefix}_{uuid.uuid4().hex[:10]}.{extension}"
#     path = os.path.join(tempfile.gettempdir(), filename)

#     file_storage.save(path)
#     return path


# def upload_to_cloudinary(file_path, folder, public_id=None):
#     """Upload an image and return its permanent HTTPS URL."""

#     result = uploader.upload(
#         file_path,
#         folder=folder,
#         public_id=public_id,
#         resource_type="image",
#     )

#     return result["secure_url"]


# def download_to_temp(url, prefix="download"):
#     """Download a registered image temporarily for comparison."""

#     filename = f"{prefix}_{uuid.uuid4().hex[:10]}.jpg"
#     path = os.path.join(tempfile.gettempdir(), filename)

#     urllib.request.urlretrieve(url, path)
#     return path


# def remove_temp_file(path):
#     """Safely remove a temporary file."""

#     try:
#         if path and os.path.exists(path):
#             os.remove(path)
#     except Exception:
#         pass


# # ---------------------------------------------------------------------
# # Pages
# # ---------------------------------------------------------------------

# @app.route("/")
# def home():
#     try:
#         products = len(list(db.products.find({})))
#     except Exception as e:
#         print("Product count error:", str(e))
#         products = 0

#     try:
#         scans = len(list(db.scans.find({})))
#     except Exception as e:
#         print("Scan count error:", str(e))
#         scans = 0

#     try:
#         chain_status = chain.chain_status()
#     except Exception as e:
#         print("Blockchain status error:", str(e))
#         chain_status = {
#             "mode": "unavailable",
#             "integrity_ok": False,
#             "blocks": 0,
#         }

#     stats = {
#         "products": products,
#         "scans": scans,
#         "chain": chain_status,
#     }

#     return render_template("index.html", stats=stats)


# @app.route("/manufacturer")
# def manufacturer_page():
#     return render_template("manufacturer_register.html")


# @app.route("/verify")
# def verify_landing():
#     return render_template("verify_scan.html")


# @app.route("/verify/<product_id>")
# def verify_product_page(product_id):
#     return render_template(
#         "verify_upload.html",
#         product_id=product_id,
#     )


# # ---------------------------------------------------------------------
# # Manufacturer registration
# # ---------------------------------------------------------------------

# @app.route("/api/register", methods=["POST"])
# def api_register():
#     temp_path = None

#     try:
#         name = request.form.get("name", "").strip()
#         manufacturer = request.form.get("manufacturer", "").strip()
#         description = request.form.get("description", "").strip()
#         image = request.files.get("original_image")

#         if (
#             not name
#             or not manufacturer
#             or not image
#             or not allowed_file(image.filename)
#         ):
#             return jsonify({
#                 "ok": False,
#                 "error": "Missing or invalid fields.",
#             }), 400

#         # Generate product ID
#         product_id = generate_product_id(manufacturer, name)

#         # Save uploaded image temporarily
#         temp_path = save_temp_upload(image, product_id)

#         # Generate SHA-256 image hash
#         image_hash = hash_image_file(temp_path)

#         # Upload original image to Cloudinary
#         image_url = upload_to_cloudinary(
#             temp_path,
#             "authentix/products",
#             product_id,
#         )

#         # Register product with the configured blockchain layer
#         block_index, tx_hash = chain.register_product(
#             product_id,
#             image_hash,
#         )

#         # Create product document
#         doc = new_product_doc(
#             product_id,
#             name,
#             manufacturer,
#             description,
#             image_url,
#             image_hash,
#             block_index,
#             tx_hash,
#         )

#         # Save using the configured database
#         db.products.insert_one(doc)

#         # Generate QR code
#         base_url = request.host_url.rstrip("/")
#         qr_url, verify_url = generate_qr(product_id, base_url)

#         return jsonify({
#             "ok": True,
#             "product_id": product_id,
#             "qr_code_url": qr_url,
#             "verify_url": verify_url,
#             "image_url": image_url,
#             "block_index": block_index,
#             "tx_hash": tx_hash,
#             "chain_mode": chain.mode,
#             "database_mode": db.mode,
#         })

#     except Exception as e:
#         print("Registration error:", str(e))

#         return jsonify({
#             "ok": False,
#             "error": "Product registration failed.",
#             "details": str(e),
#         }), 500

#     finally:
#         remove_temp_file(temp_path)


# # ---------------------------------------------------------------------
# # Get registered product
# # ---------------------------------------------------------------------

# @app.route("/api/product/<product_id>")
# def api_get_product(product_id):
#     try:
#         product = db.products.find_one({
#             "product_id": product_id,
#         })

#         if not product:
#             return jsonify({
#                 "ok": False,
#                 "error": "Product not found.",
#             }), 404

#         record = chain.get_record(product_id)
#         on_chain = record is not None

#         # Remove MongoDB ObjectId before JSON serialization
#         product.pop("_id", None)

#         return jsonify({
#             "ok": True,
#             "product": product,
#             "on_chain": on_chain,
#             "chain_mode": chain.mode,
#             "database_mode": db.mode,
#         })

#     except Exception as e:
#         print("Get product error:", str(e))

#         return jsonify({
#             "ok": False,
#             "error": "Unable to retrieve product.",
#             "details": str(e),
#         }), 500


# # ---------------------------------------------------------------------
# # Product verification
# # ---------------------------------------------------------------------

# @app.route("/api/verify/<product_id>", methods=["POST"])
# def api_verify(product_id):
#     captured_path = None
#     original_path = None

#     try:
#         # Find registered product
#         product = db.products.find_one({
#             "product_id": product_id,
#         })

#         if not product:
#             return jsonify({
#                 "ok": False,
#                 "error": "Product not found.",
#             }), 404

#         # Get customer's uploaded product image
#         image = request.files.get("captured_image")

#         if not image or not allowed_file(image.filename):
#             return jsonify({
#                 "ok": False,
#                 "error": "Please provide a valid product image.",
#             }), 400

#         # Save customer's image temporarily
#         captured_path = save_temp_upload(
#             image,
#             f"scan_{product_id}",
#         )

#         # Upload customer's image to Cloudinary
#         captured_url = upload_to_cloudinary(
#             captured_path,
#             "authentix/scans",
#         )

#         # Get original registered image URL
#         original_url = product.get("original_image_path")

#         if not original_url:
#             return jsonify({
#                 "ok": False,
#                 "error": "Original product image is missing.",
#             }), 500

#         # Download original image temporarily
#         original_path = download_to_temp(
#             original_url,
#             "original",
#         )

#         # Compare registered and captured images
#         result = ai_verify.compare_images(
#             original_path,
#             captured_path,
#         )

#         # Save verification scan
#         scan_doc = new_scan_doc(
#             product_id,
#             result["similarity"],
#             result["verdict"],
#             captured_url,
#         )

#         db.scans.insert_one(scan_doc)

#         return jsonify({
#             "ok": True,
#             "product_name": product["name"],
#             "manufacturer": product["manufacturer"],
#             "similarity": result["similarity"],
#             "verdict": result["verdict"],
#             "regions_analyzed": result["regions_analyzed"],
#             "deep_features_used": result["deep_features_used"],
#             "captured_image_url": captured_url,
#             "original_image_url": original_url,
#             "database_mode": db.mode,
#             "chain_mode": chain.mode,
#         })

#     except Exception as e:
#         print("Verification error:", str(e))

#         return jsonify({
#             "ok": False,
#             "error": "Product verification failed.",
#             "details": str(e),
#         }), 500

#     finally:
#         remove_temp_file(captured_path)
#         remove_temp_file(original_path)


# # ---------------------------------------------------------------------
# # Blockchain status
# # ---------------------------------------------------------------------

# @app.route("/api/chain-status")
# def api_chain_status():
#     try:
#         return jsonify(chain.chain_status())

#     except Exception as e:
#         print("Blockchain status error:", str(e))

#         return jsonify({
#             "mode": "unavailable",
#             "integrity_ok": False,
#             "blocks": 0,
#             "error": str(e),
#         }), 500


# # ---------------------------------------------------------------------
# # Health check and database diagnostics
# # ---------------------------------------------------------------------

# @app.route("/api/health")
# def health():
#     database_error = getattr(
#         db,
#         "connection_error",
#         "No database error details available. Check models.py.",
#     )

#     return jsonify({
#         "ok": True,
#         "database": db.mode,
#         "database_error": database_error,
#         "blockchain": chain.mode,
#         "cloudinary": bool(
#             os.environ.get("CLOUDINARY_CLOUD_NAME")
#             and os.environ.get("CLOUDINARY_API_KEY")
#             and os.environ.get("CLOUDINARY_API_SECRET")
#         ),
#     })


# # ---------------------------------------------------------------------
# # Local development
# # ---------------------------------------------------------------------

# if __name__ == "__main__":
#     app.run(
#         debug=True,
#         host="0.0.0.0",
#         port=5000,
#     )



import os
import uuid
import tempfile
import urllib.request

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

import cloudinary
from cloudinary import uploader

from models import db, new_product_doc, new_scan_doc
from blockchain_client import chain
from qr_utils import generate_product_id, generate_qr, hash_image_file
import ai_verify


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ALLOWED_EXT = {"png", "jpg", "jpeg", "webp"}

app = Flask(__name__)
CORS(app)

# Maximum upload size: 16 MB
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024


# ---------------------------------------------------------------------
# Cloudinary configuration
# ---------------------------------------------------------------------

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True,
)


# ---------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------

def allowed_file(filename):
    """Check whether the uploaded file has an allowed extension."""

    if not filename or "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()
    return extension in ALLOWED_EXT


def save_temp_upload(file_storage, prefix):
    """Save an uploaded image temporarily."""

    original_filename = file_storage.filename or ""

    if "." not in original_filename:
        raise ValueError("The uploaded file must have an extension.")

    extension = original_filename.rsplit(".", 1)[1].lower()

    filename = f"{prefix}_{uuid.uuid4().hex[:10]}.{extension}"
    path = os.path.join(tempfile.gettempdir(), filename)

    file_storage.save(path)
    return path


def upload_to_cloudinary(file_path, folder, public_id=None):
    """Upload an image and return its permanent HTTPS URL."""

    result = uploader.upload(
        file_path,
        folder=folder,
        public_id=public_id,
        resource_type="image",
    )

    return result["secure_url"]


def download_to_temp(url, prefix="download"):
    """Download a registered image temporarily for comparison."""

    filename = f"{prefix}_{uuid.uuid4().hex[:10]}.jpg"
    path = os.path.join(tempfile.gettempdir(), filename)

    request_obj = urllib.request.Request(
        url,
        headers={"User-Agent": "Authentix/1.0"},
    )

    try:
        with urllib.request.urlopen(request_obj, timeout=20) as response:
            with open(path, "wb") as output_file:
                output_file.write(response.read())
    except Exception:
        remove_temp_file(path)
        raise

    return path


def remove_temp_file(path):
    """Safely remove a temporary file."""

    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


# ---------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------

@app.route("/")
def home():
    try:
        products = len(list(db.products.find({})))
    except Exception as e:
        print("Product count error:", str(e))
        products = 0

    try:
        scans = len(list(db.scans.find({})))
    except Exception as e:
        print("Scan count error:", str(e))
        scans = 0

    try:
        chain_status = chain.chain_status()
    except Exception as e:
        print("Blockchain status error:", str(e))
        chain_status = {
            "mode": "unavailable",
            "integrity_ok": False,
            "blocks": 0,
        }

    stats = {
        "products": products,
        "scans": scans,
        "chain": chain_status,
    }

    return render_template("index.html", stats=stats)


@app.route("/manufacturer")
def manufacturer_page():
    return render_template("manufacturer_register.html")


@app.route("/verify")
def verify_landing():
    return render_template("verify_scan.html")


@app.route("/verify/<product_id>")
def verify_product_page(product_id):
    return render_template(
        "verify_upload.html",
        product_id=product_id,
    )


# ---------------------------------------------------------------------
# Manufacturer registration
# ---------------------------------------------------------------------

@app.route("/api/register", methods=["POST"])
def api_register():
    temp_path = None

    try:
        name = request.form.get("name", "").strip()
        manufacturer = request.form.get("manufacturer", "").strip()
        description = request.form.get("description", "").strip()
        image = request.files.get("original_image")

        if (
            not name
            or not manufacturer
            or not image
            or not allowed_file(image.filename)
        ):
            return jsonify({
                "ok": False,
                "error": "Missing or invalid fields.",
            }), 400

        # Generate product ID
        product_id = generate_product_id(manufacturer, name)

        # Save uploaded image temporarily
        temp_path = save_temp_upload(image, product_id)

        # Generate SHA-256 hash from the original uploaded file
        image_hash = hash_image_file(temp_path)

        # Upload original image to Cloudinary
        image_url = upload_to_cloudinary(
            temp_path,
            "authentix/products",
            product_id,
        )

        # Register product with configured blockchain layer
        block_index, tx_hash = chain.register_product(
            product_id,
            image_hash,
        )

        # Create product document
        doc = new_product_doc(
            product_id,
            name,
            manufacturer,
            description,
            image_url,
            image_hash,
            block_index,
            tx_hash,
        )

        # Save product
        db.products.insert_one(doc)

        # Generate QR code
        base_url = request.host_url.rstrip("/")
        qr_url, verify_url = generate_qr(product_id, base_url)

        return jsonify({
            "ok": True,
            "product_id": product_id,
            "qr_code_url": qr_url,
            "verify_url": verify_url,
            "image_url": image_url,
            "block_index": block_index,
            "tx_hash": tx_hash,
            "chain_mode": chain.mode,
            "database_mode": db.mode,
        })

    except Exception as e:
        print("Registration error:", str(e))

        return jsonify({
            "ok": False,
            "error": "Product registration failed.",
            "details": str(e),
        }), 500

    finally:
        remove_temp_file(temp_path)


# ---------------------------------------------------------------------
# Get registered product
# ---------------------------------------------------------------------

@app.route("/api/product/<product_id>")
def api_get_product(product_id):
    try:
        product = db.products.find_one({
            "product_id": product_id,
        })

        if not product:
            return jsonify({
                "ok": False,
                "error": "Product not found.",
            }), 404

        record = chain.get_record(product_id)
        on_chain = record is not None

        # Remove MongoDB ObjectId before JSON serialization
        product.pop("_id", None)

        return jsonify({
            "ok": True,
            "product": product,
            "on_chain": on_chain,
            "chain_mode": chain.mode,
            "database_mode": db.mode,
        })

    except Exception as e:
        print("Get product error:", str(e))

        return jsonify({
            "ok": False,
            "error": "Unable to retrieve product.",
            "details": str(e),
        }), 500


# ---------------------------------------------------------------------
# Product verification
# ---------------------------------------------------------------------

@app.route("/api/verify/<product_id>", methods=["POST"])
def api_verify(product_id):
    captured_path = None
    original_path = None

    try:
        # Find registered product
        product = db.products.find_one({
            "product_id": product_id,
        })

        if not product:
            return jsonify({
                "ok": False,
                "error": "Product not found.",
            }), 404

        # Get customer's uploaded image
        image = request.files.get("captured_image")

        if not image or not allowed_file(image.filename):
            return jsonify({
                "ok": False,
                "error": "Please provide a valid product image.",
            }), 400

        # Save customer's image temporarily
        captured_path = save_temp_upload(
            image,
            f"scan_{product_id}",
        )

        # Get original registered image URL
        original_url = product.get("original_image_path")

        if not original_url:
            return jsonify({
                "ok": False,
                "error": "Original product image is missing.",
            }), 500

        # -------------------------------------------------------------
        # FIX: Check exact image hash before ORB comparison
        # -------------------------------------------------------------

        captured_hash = hash_image_file(captured_path)
        registered_hash = product.get("image_hash")

        if registered_hash and captured_hash == registered_hash:
            # Uploaded file is byte-for-byte identical to the
            # image that was registered for this product.
            result = {
                "similarity": 100.0,
                "verdict": "AUTHENTIC",
                "regions_analyzed": 0,
                "deep_features_used": False,
            }

            print(
                f"Exact image hash match for {product_id}: AUTHENTIC"
            )

        else:
            # Upload customer's image to Cloudinary
            captured_url = upload_to_cloudinary(
                captured_path,
                "authentix/scans",
            )

            # Download original only when visual comparison is needed
            original_path = download_to_temp(
                original_url,
                "original",
            )

            # Compare registered and captured images
            result = ai_verify.compare_images(
                original_path,
                captured_path,
            )

            print(
                f"Visual comparison for {product_id}: {result}"
            )

        # -------------------------------------------------------------
        # Upload captured image for scan history
        # -------------------------------------------------------------

        # Upload in both branches. This ensures the exact-match case
        # also gets a captured image URL for the scan record.
        if registered_hash and captured_hash == registered_hash:
            captured_url = upload_to_cloudinary(
                captured_path,
                "authentix/scans",
            )

        # Save verification scan
        scan_doc = new_scan_doc(
            product_id,
            result["similarity"],
            result["verdict"],
            captured_url,
        )

        db.scans.insert_one(scan_doc)

        return jsonify({
            "ok": True,
            "product_name": product["name"],
            "manufacturer": product["manufacturer"],
            "similarity": result["similarity"],
            "verdict": result["verdict"],
            "regions_analyzed": result["regions_analyzed"],
            "deep_features_used": result["deep_features_used"],
            "captured_image_url": captured_url,
            "original_image_url": original_url,
            "database_mode": db.mode,
            "chain_mode": chain.mode,
        })

    except Exception as e:
        print("Verification error:", str(e))

        return jsonify({
            "ok": False,
            "error": "Product verification failed.",
            "details": str(e),
        }), 500

    finally:
        remove_temp_file(captured_path)
        remove_temp_file(original_path)


# ---------------------------------------------------------------------
# Blockchain status
# ---------------------------------------------------------------------

@app.route("/api/chain-status")
def api_chain_status():
    try:
        return jsonify(chain.chain_status())

    except Exception as e:
        print("Blockchain status error:", str(e))

        return jsonify({
            "mode": "unavailable",
            "integrity_ok": False,
            "blocks": 0,
            "error": str(e),
        }), 500


# ---------------------------------------------------------------------
# Health check and database diagnostics
# ---------------------------------------------------------------------

@app.route("/api/health")
def health():
    database_error = getattr(
        db,
        "connection_error",
        "No database error details available. Check models.py.",
    )

    return jsonify({
        "ok": True,
        "database": db.mode,
        "database_error": database_error,
        "blockchain": chain.mode,
        "cloudinary": bool(
            os.environ.get("CLOUDINARY_CLOUD_NAME")
            and os.environ.get("CLOUDINARY_API_KEY")
            and os.environ.get("CLOUDINARY_API_SECRET")
        ),
    })


# ---------------------------------------------------------------------
# Local development
# ---------------------------------------------------------------------

if __name__ == "__main__":
    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000,
    )
