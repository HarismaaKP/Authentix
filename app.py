# import os
# import uuid

# from flask import Flask, render_template, request, jsonify, redirect, url_for
# from flask_cors import CORS

# from models import db, new_product_doc, new_scan_doc
# from blockchain_client import chain
# from qr_utils import generate_product_id, generate_qr, hash_image_file
# import ai_verify


# # ---------------------------------------------------------------
# # Configuration
# # ---------------------------------------------------------------

# BASE_DIR = os.path.dirname(__file__)

# UPLOAD_DIR = os.path.join(
#     BASE_DIR,
#     "static",
#     "uploads"
# )

# ALLOWED_EXT = {
#     "png",
#     "jpg",
#     "jpeg",
#     "webp"
# }


# # ---------------------------------------------------------------
# # Flask App
# # ---------------------------------------------------------------

# app = Flask(__name__)

# CORS(app)

# app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024


# # Create required folders
# os.makedirs(UPLOAD_DIR, exist_ok=True)

# os.makedirs(
#     os.path.join(BASE_DIR, "static", "qrcodes"),
#     exist_ok=True
# )


# # ---------------------------------------------------------------
# # Helper Functions
# # ---------------------------------------------------------------

# def allowed_file(filename):
#     """
#     Check whether the uploaded file has an allowed extension.
#     """

#     return (
#         "." in filename
#         and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT
#     )


# def save_upload(file_storage, prefix):
#     """
#     Save an uploaded image into static/uploads.
#     """

#     ext = file_storage.filename.rsplit(".", 1)[1].lower()

#     filename = f"{prefix}_{uuid.uuid4().hex[:10]}.{ext}"

#     path = os.path.join(
#         UPLOAD_DIR,
#         filename
#     )

#     file_storage.save(path)

#     url = f"/static/uploads/{filename}"

#     return path, url


# # ----------------------------------------------------------------
# # Pages
# # ----------------------------------------------------------------

# @app.route("/")
# def home():

#     stats = {
#         # FIX:
#         # MongoDB find() returns a Cursor.
#         # Cursor cannot be used with len().
#         "products": (
#             db.products.count_documents({})
#             if hasattr(db.products, "count_documents")
#             else len(db.products)
#         ),

#         "scans": (
#             db.scans.count_documents({})
#             if hasattr(db.scans, "count_documents")
#             else len(db.scans)
#         ),

#         "chain": chain.chain_status(),
#     }

#     return render_template(
#         "index.html",
#         stats=stats
#     )


# @app.route("/manufacturer")
# def manufacturer_page():

#     return render_template(
#         "manufacturer_register.html"
#     )


# @app.route("/verify")
# def verify_landing():

#     return render_template(
#         "verify_scan.html"
#     )


# @app.route("/verify/<product_id>")
# def verify_product_page(product_id):

#     return render_template(
#         "verify_upload.html",
#         product_id=product_id
#     )


# # ----------------------------------------------------------------
# # API - Register Product
# # ----------------------------------------------------------------

# @app.route("/api/register", methods=["POST"])
# def api_register():

#     name = request.form.get(
#         "name",
#         ""
#     ).strip()

#     manufacturer = request.form.get(
#         "manufacturer",
#         ""
#     ).strip()

#     description = request.form.get(
#         "description",
#         ""
#     ).strip()

#     image = request.files.get(
#         "original_image"
#     )


#     # Validate input
#     if (
#         not name
#         or not manufacturer
#         or not image
#         or not allowed_file(image.filename)
#     ):
#         return jsonify({
#             "ok": False,
#             "error": "Missing or invalid fields."
#         }), 400


#     # Generate unique product ID
#     product_id = generate_product_id(
#         manufacturer,
#         name
#     )


#     # Save original product image
#     img_path, img_url = save_upload(
#         image,
#         product_id
#     )


#     # Create image hash
#     image_hash = hash_image_file(
#         img_path
#     )


#     # Register product on blockchain
#     block_index, tx_hash = chain.register_product(
#         product_id,
#         image_hash
#     )


#     # Create MongoDB document
#     doc = new_product_doc(
#         product_id,
#         name,
#         manufacturer,
#         description,
#         img_url,
#         image_hash,
#         block_index,
#         tx_hash
#     )


#     # Save product to MongoDB
#     db.products.insert_one(doc)


#     # Generate QR code
#     base_url = request.host_url.rstrip("/")

#     qr_url, verify_url = generate_qr(
#         product_id,
#         base_url
#     )


#     # Return result
#     return jsonify({
#         "ok": True,
#         "product_id": product_id,
#         "qr_code_url": qr_url,
#         "verify_url": verify_url,
#         "block_index": block_index,
#         "tx_hash": tx_hash,
#         "chain_mode": chain.mode,
#     })


# # ----------------------------------------------------------------
# # API - Get Product
# # ----------------------------------------------------------------

# @app.route("/api/product/<product_id>")
# def api_get_product(product_id):

#     product = db.products.find_one({
#         "product_id": product_id
#     })


#     if not product:
#         return jsonify({
#             "ok": False,
#             "error": "Product not found."
#         }), 404


#     # Get blockchain record
#     record = chain.get_record(
#         product_id
#     )

#     on_chain = record is not None


#     # Remove MongoDB internal ID
#     product.pop(
#         "_id",
#         None
#     )


#     return jsonify({
#         "ok": True,
#         "product": product,
#         "on_chain": on_chain,
#         "chain_mode": chain.mode
#     })


# # ----------------------------------------------------------------
# # API - Verify Product
# # ----------------------------------------------------------------

# @app.route(
#     "/api/verify/<product_id>",
#     methods=["POST"]
# )
# def api_verify(product_id):

#     # Find product in MongoDB
#     product = db.products.find_one({
#         "product_id": product_id
#     })


#     if not product:
#         return jsonify({
#             "ok": False,
#             "error": "Product not registered on blockchain."
#         }), 404


#     # Get uploaded/captured image
#     image = request.files.get(
#         "captured_image"
#     )


#     # Validate image
#     if (
#         not image
#         or not allowed_file(image.filename)
#     ):
#         return jsonify({
#             "ok": False,
#             "error": "Please provide a product image."
#         }), 400


#     # Save captured image
#     captured_path, captured_url = save_upload(
#         image,
#         f"scan_{product_id}"
#     )


#     # Find original product image
#     original_path = os.path.join(
#         BASE_DIR,
#         product["original_image_path"].lstrip("/")
#     )


#     # Compare original and captured images using AI
#     result = ai_verify.compare_images(
#         original_path,
#         captured_path
#     )


#     # Create scan document
#     scan_doc = new_scan_doc(
#         product_id,
#         result["similarity"],
#         result["verdict"],
#         captured_url
#     )


#     # Save scan information
#     db.scans.insert_one(
#         scan_doc
#     )


#     # Return verification result
#     return jsonify({
#         "ok": True,
#         "product_name": product["name"],
#         "manufacturer": product["manufacturer"],
#         "similarity": result["similarity"],
#         "verdict": result["verdict"],
#         "regions_analyzed": result["regions_analyzed"],
#         "deep_features_used": result["deep_features_used"],
#         "captured_image_url": captured_url,
#         "original_image_url": product["original_image_path"],
#     })


# # ----------------------------------------------------------------
# # API - Blockchain Status
# # ----------------------------------------------------------------

# @app.route("/api/chain-status")
# def api_chain_status():

#     return jsonify(
#         chain.chain_status()
#     )


# # ----------------------------------------------------------------
# # Start Flask Server
# # ----------------------------------------------------------------

# if __name__ == "__main__":

#     app.run(
#         debug=True,
#         host="0.0.0.0",
#         port=5000
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

# Maximum upload size = 16 MB
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
    """
    Save an uploaded file temporarily.

    Vercel allows temporary files in /tmp.
    These files are NOT used for permanent storage.
    """

    extension = file_storage.filename.rsplit(".", 1)[1].lower()

    filename = f"{prefix}_{uuid.uuid4().hex[:10]}.{extension}"

    temp_dir = tempfile.gettempdir()

    path = os.path.join(temp_dir, filename)

    file_storage.save(path)

    return path


def upload_to_cloudinary(file_path, folder, public_id=None):
    """
    Upload an image to Cloudinary.

    Returns the permanent HTTPS image URL.
    """

    result = uploader.upload(
        file_path,
        folder=folder,
        public_id=public_id,
        resource_type="image",
    )

    return result["secure_url"]


def download_to_temp(url, prefix="download"):
    """
    Download a Cloudinary image temporarily for AI comparison.
    """

    extension = ".jpg"

    filename = f"{prefix}_{uuid.uuid4().hex[:10]}{extension}"

    path = os.path.join(
        tempfile.gettempdir(),
        filename
    )

    urllib.request.urlretrieve(url, path)

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
    except Exception:
        products = 0

    try:
        scans = len(list(db.scans.find({})))
    except Exception:
        scans = 0

    try:
        chain_status = chain.chain_status()
    except Exception:
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

    return render_template(
        "index.html",
        stats=stats
    )


@app.route("/manufacturer")
def manufacturer_page():

    return render_template(
        "manufacturer_register.html"
    )


@app.route("/verify")
def verify_landing():

    return render_template(
        "verify_scan.html"
    )


@app.route("/verify/<product_id>")
def verify_product_page(product_id):

    return render_template(
        "verify_upload.html",
        product_id=product_id
    )


# ---------------------------------------------------------------------
# Manufacturer registration
# ---------------------------------------------------------------------

@app.route("/api/register", methods=["POST"])
def api_register():

    temp_path = None

    try:

        name = request.form.get(
            "name",
            ""
        ).strip()

        manufacturer = request.form.get(
            "manufacturer",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        image = request.files.get(
            "original_image"
        )

        # Validate input
        if (
            not name
            or not manufacturer
            or not image
            or not allowed_file(image.filename)
        ):
            return jsonify({
                "ok": False,
                "error": "Missing or invalid fields."
            }), 400

        # -------------------------------------------------------------
        # 1. Generate product ID
        # -------------------------------------------------------------

        product_id = generate_product_id(
            manufacturer,
            name
        )

        # -------------------------------------------------------------
        # 2. Save image temporarily
        # -------------------------------------------------------------

        temp_path = save_temp_upload(
            image,
            product_id
        )

        # -------------------------------------------------------------
        # 3. Generate SHA-256 image hash
        # -------------------------------------------------------------

        image_hash = hash_image_file(
            temp_path
        )

        # -------------------------------------------------------------
        # 4. Upload original image to Cloudinary
        # -------------------------------------------------------------

        image_url = upload_to_cloudinary(
            temp_path,
            "authentix/products",
            product_id
        )

        # -------------------------------------------------------------
        # 5. Register product on blockchain
        # -------------------------------------------------------------

        block_index, tx_hash = chain.register_product(
            product_id,
            image_hash
        )

        # -------------------------------------------------------------
        # 6. Save product information in MongoDB
        # -------------------------------------------------------------

        doc = new_product_doc(
            product_id,
            name,
            manufacturer,
            description,
            image_url,
            image_hash,
            block_index,
            tx_hash
        )

        db.products.insert_one(doc)

        # -------------------------------------------------------------
        # 7. Generate QR code
        # -------------------------------------------------------------

        base_url = request.host_url.rstrip("/")

        qr_url, verify_url = generate_qr(
            product_id,
            base_url
        )

        # -------------------------------------------------------------
        # Response
        # -------------------------------------------------------------

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

        remove_temp_file(
            temp_path
        )


# ---------------------------------------------------------------------
# Get product
# ---------------------------------------------------------------------

@app.route("/api/product/<product_id>")
def api_get_product(product_id):

    try:

        product = db.products.find_one({
            "product_id": product_id
        })

        if not product:

            return jsonify({
                "ok": False,
                "error": "Product not found."
            }), 404

        # Check blockchain record
        record = chain.get_record(
            product_id
        )

        on_chain = record is not None

        # Remove MongoDB ObjectId if present
        if "_id" in product:

            product.pop(
                "_id",
                None
            )

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

        # -------------------------------------------------------------
        # 1. Find registered product
        # -------------------------------------------------------------

        product = db.products.find_one({
            "product_id": product_id
        })

        if not product:

            return jsonify({
                "ok": False,
                "error": "Product not found."
            }), 404

        # -------------------------------------------------------------
        # 2. Get customer's uploaded image
        # -------------------------------------------------------------

        image = request.files.get(
            "captured_image"
        )

        if (
            not image
            or not allowed_file(image.filename)
        ):
            return jsonify({
                "ok": False,
                "error": "Please provide a product image."
            }), 400

        # -------------------------------------------------------------
        # 3. Save captured image temporarily
        # -------------------------------------------------------------

        captured_path = save_temp_upload(
            image,
            f"scan_{product_id}"
        )

        # -------------------------------------------------------------
        # 4. Upload captured image to Cloudinary
        # -------------------------------------------------------------

        captured_url = upload_to_cloudinary(
            captured_path,
            "authentix/scans"
        )

        # -------------------------------------------------------------
        # 5. Download original registered image temporarily
        # -------------------------------------------------------------

        original_url = product.get(
            "original_image_path"
        )

        if not original_url:

            return jsonify({
                "ok": False,
                "error": "Original product image is missing."
            }), 500

        original_path = download_to_temp(
            original_url,
            "original"
        )

        # -------------------------------------------------------------
        # 6. Compare images using AI/CV module
        # -------------------------------------------------------------

        result = ai_verify.compare_images(
            original_path,
            captured_path
        )

        # -------------------------------------------------------------
        # 7. Save verification scan in MongoDB
        # -------------------------------------------------------------

        scan_doc = new_scan_doc(
            product_id,
            result["similarity"],
            result["verdict"],
            captured_url
        )

        db.scans.insert_one(
            scan_doc
        )

        # -------------------------------------------------------------
        # 8. Return result
        # -------------------------------------------------------------

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

        remove_temp_file(
            captured_path
        )

        remove_temp_file(
            original_path
        )


# ---------------------------------------------------------------------
# Blockchain status
# ---------------------------------------------------------------------

@app.route("/api/chain-status")
def api_chain_status():

    try:

        return jsonify(
            chain.chain_status()
        )

    except Exception as e:

        return jsonify({
            "mode": "unavailable",
            "integrity_ok": False,
            "blocks": 0,
            "error": str(e),
        })


# ---------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------

@app.route("/api/health")
def health():

    return jsonify({
        "ok": True,
        "database": db.mode,
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
        port=5000
    )
