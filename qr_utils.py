import os
import uuid
import hashlib
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
from qrcode.image.styles.colormasks import SolidFillColorMask

QR_DIR = os.path.join(os.path.dirname(__file__), "static", "qrcodes")


def generate_product_id(manufacturer, name):
    raw = f"{manufacturer}-{name}-{uuid.uuid4()}"
    return "AUX-" + hashlib.sha256(raw.encode()).hexdigest()[:12].upper()


def hash_image_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def generate_qr(product_id, base_url="http://localhost:5000"):
    verify_url = f"{base_url}/verify/{product_id}"
    try:
        img = qrcode.make(
            verify_url,
            image_factory=StyledPilImage,
            module_drawer=RoundedModuleDrawer(),
            color_mask=SolidFillColorMask(front_color=(79, 70, 229), back_color=(255, 255, 255)),
        )
    except Exception:
        img = qrcode.make(verify_url)
    filename = f"{product_id}.png"
    path = os.path.join(QR_DIR, filename)
    img.save(path)
    return f"/static/qrcodes/{filename}", verify_url


