import os
import uuid

from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS

from models import db, new_product_doc, new_scan_doc
from blockchain_client import chain
from qr_utils import generate_product_id, generate_qr, hash_image_file
import ai_verify


# ---------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------

BASE_DIR = os.path.dirname(__file__)

UPLOAD_DIR = os.path.join(
    BASE_DIR,
    "static",
    "uploads"
)

ALLOWED_EXT = {
    "png",
    "jpg",
    "jpeg",
    "webp"
}


# ---------------------------------------------------------------
# Flask App
# ---------------------------------------------------------------

app = Flask(__name__)

CORS(app)

app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024


# Create required folders
os.makedirs(UPLOAD_DIR, exist_ok=True)

os.makedirs(
    os.path.join(BASE_DIR, "static", "qrcodes"),
    exist_ok=True
)


# ---------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------

def allowed_file(filename):
    """
    Check whether the uploaded file has an allowed extension.
    """

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT
    )


def save_upload(file_storage, prefix):
    """
    Save an uploaded image into static/uploads.
    """

    ext = file_storage.filename.rsplit(".", 1)[1].lower()

    filename = f"{prefix}_{uuid.uuid4().hex[:10]}.{ext}"

    path = os.path.join(
        UPLOAD_DIR,
        filename
    )

    file_storage.save(path)

    url = f"/static/uploads/{filename}"

    return path, url


# ----------------------------------------------------------------
# Pages
# ----------------------------------------------------------------

@app.route("/")
def home():

    stats = {
        # FIX:
        # MongoDB find() returns a Cursor.
        # Cursor cannot be used with len().
        "products": (
            db.products.count_documents({})
            if hasattr(db.products, "count_documents")
            else len(db.products)
        ),

        "scans": (
            db.scans.count_documents({})
            if hasattr(db.scans, "count_documents")
            else len(db.scans)
        ),

        "chain": chain.chain_status(),
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


# ----------------------------------------------------------------
# API - Register Product
# ----------------------------------------------------------------

@app.route("/api/register", methods=["POST"])
def api_register():

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


    # Generate unique product ID
    product_id = generate_product_id(
        manufacturer,
        name
    )


    # Save original product image
    img_path, img_url = save_upload(
        image,
        product_id
    )


    # Create image hash
    image_hash = hash_image_file(
        img_path
    )


    # Register product on blockchain
    block_index, tx_hash = chain.register_product(
        product_id,
        image_hash
    )


    # Create MongoDB document
    doc = new_product_doc(
        product_id,
        name,
        manufacturer,
        description,
        img_url,
        image_hash,
        block_index,
        tx_hash
    )


    # Save product to MongoDB
    db.products.insert_one(doc)


    # Generate QR code
    base_url = request.host_url.rstrip("/")

    qr_url, verify_url = generate_qr(
        product_id,
        base_url
    )


    # Return result
    return jsonify({
        "ok": True,
        "product_id": product_id,
        "qr_code_url": qr_url,
        "verify_url": verify_url,
        "block_index": block_index,
        "tx_hash": tx_hash,
        "chain_mode": chain.mode,
    })


# ----------------------------------------------------------------
# API - Get Product
# ----------------------------------------------------------------

@app.route("/api/product/<product_id>")
def api_get_product(product_id):

    product = db.products.find_one({
        "product_id": product_id
    })


    if not product:
        return jsonify({
            "ok": False,
            "error": "Product not found."
        }), 404


    # Get blockchain record
    record = chain.get_record(
        product_id
    )

    on_chain = record is not None


    # Remove MongoDB internal ID
    product.pop(
        "_id",
        None
    )


    return jsonify({
        "ok": True,
        "product": product,
        "on_chain": on_chain,
        "chain_mode": chain.mode
    })


# ----------------------------------------------------------------
# API - Verify Product
# ----------------------------------------------------------------

@app.route(
    "/api/verify/<product_id>",
    methods=["POST"]
)
def api_verify(product_id):

    # Find product in MongoDB
    product = db.products.find_one({
        "product_id": product_id
    })


    if not product:
        return jsonify({
            "ok": False,
            "error": "Product not registered on blockchain."
        }), 404


    # Get uploaded/captured image
    image = request.files.get(
        "captured_image"
    )


    # Validate image
    if (
        not image
        or not allowed_file(image.filename)
    ):
        return jsonify({
            "ok": False,
            "error": "Please provide a product image."
        }), 400


    # Save captured image
    captured_path, captured_url = save_upload(
        image,
        f"scan_{product_id}"
    )


    # Find original product image
    original_path = os.path.join(
        BASE_DIR,
        product["original_image_path"].lstrip("/")
    )


    # Compare original and captured images using AI
    result = ai_verify.compare_images(
        original_path,
        captured_path
    )


    # Create scan document
    scan_doc = new_scan_doc(
        product_id,
        result["similarity"],
        result["verdict"],
        captured_url
    )


    # Save scan information
    db.scans.insert_one(
        scan_doc
    )


    # Return verification result
    return jsonify({
        "ok": True,
        "product_name": product["name"],
        "manufacturer": product["manufacturer"],
        "similarity": result["similarity"],
        "verdict": result["verdict"],
        "regions_analyzed": result["regions_analyzed"],
        "deep_features_used": result["deep_features_used"],
        "captured_image_url": captured_url,
        "original_image_url": product["original_image_path"],
    })


# ----------------------------------------------------------------
# API - Blockchain Status
# ----------------------------------------------------------------

@app.route("/api/chain-status")
def api_chain_status():

    return jsonify(
        chain.chain_status()
    )


# ----------------------------------------------------------------
# Start Flask Server
# ----------------------------------------------------------------

if __name__ == "__main__":

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )

