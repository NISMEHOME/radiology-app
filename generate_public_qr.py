import qrcode
import os

folder = os.path.join("app", "static", "qr_codes")
os.makedirs(folder, exist_ok=True)

qr_url = "http://127.0.0.1:5000/radiology/qr-entry"

filepath = os.path.join(folder, "public_radiology_qr.png")

img = qrcode.make(qr_url)
img.save(filepath)

print("QR public généré :", filepath)