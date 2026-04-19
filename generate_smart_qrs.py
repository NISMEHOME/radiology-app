import os
import qrcode
from PIL import Image, ImageDraw, ImageFilter

# =========================================================
# ⚙️ CONFIG
# =========================================================
BASE_URL = "http://127.0.0.1:5000"

QR_CONFIGS = {
    "normal": {
        "route": "/radiology/scan/normal",
        "colors": ((0, 90, 200), (0, 180, 255)),
    },
    "emergency": {
        "route": "/radiology/scan/emergency",
        "colors": ((220, 53, 69), (255, 140, 0)),
    },
    "recommendation": {
        "route": "/radiology/scan/recommendation",
        "colors": ((25, 135, 84), (0, 200, 140)),
    },
}

STATIC_FOLDER = os.path.join("app", "static")
QR_FOLDER = os.path.join(STATIC_FOLDER, "qr_codes")
LOGO = os.path.join(STATIC_FOLDER, "logo_radiologie.png")

os.makedirs(QR_FOLDER, exist_ok=True)


# =========================================================
# 🌈 DÉGRADÉ
# =========================================================
def diagonal_gradient(size, c1, c2):
    img = Image.new("RGB", size)
    draw = ImageDraw.Draw(img)

    width, height = size

    for y in range(height):
        for x in range(width):
            ratio = (x + y) / (width + height)
            r = int(c1[0] * (1 - ratio) + c2[0] * ratio)
            g = int(c1[1] * (1 - ratio) + c2[1] * ratio)
            b = int(c1[2] * (1 - ratio) + c2[2] * ratio)
            draw.point((x, y), fill=(r, g, b))

    return img


# =========================================================
# 📲 QR PREMIUM SCANNABLE
# =========================================================
def generate_premium_qr(name, route, colors):
    qr = qrcode.QRCode(
        version=4,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=20,
        border=4,
    )

    qr.add_data(BASE_URL + route)
    qr.make(fit=True)

    matrix = qr.get_matrix()
    size = len(matrix)

    module = 16
    padding = 40
    canvas_size = size * module + padding * 2

    # fond blanc net
    canvas = Image.new("RGBA", (canvas_size, canvas_size), "white")
    draw = ImageDraw.Draw(canvas)

    gradient = diagonal_gradient(
        (canvas_size, canvas_size),
        colors[0],
        colors[1],
    )

    # =========================================================
    # 🎨 QR BIEN VISIBLE
    # =========================================================
    for y in range(size):
        for x in range(size):
            if matrix[y][x]:
                x1 = padding + x * module
                y1 = padding + y * module
                x2 = x1 + module - 2
                y2 = y1 + module - 2

                color = gradient.getpixel((x1, y1))

                draw.rounded_rectangle(
                    (x1, y1, x2, y2),
                    radius=4,
                    fill=color,
                )

    # =========================================================
    # 🏥 LOGO CENTRAL PETIT ET SAFE
    # =========================================================
    badge_size = canvas_size // 6

    # ombre
    shadow = Image.new(
        "RGBA",
        (badge_size + 10, badge_size + 10),
        (0, 0, 0, 0),
    )
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.ellipse(
        (5, 5, badge_size + 5, badge_size + 5),
        fill=(0, 0, 0, 35),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(5))

    shadow_pos = (
        (canvas_size - shadow.size[0]) // 2,
        (canvas_size - shadow.size[1]) // 2,
    )
    canvas.paste(shadow, shadow_pos, shadow)

    # badge blanc
    badge = Image.new(
        "RGBA",
        (badge_size, badge_size),
        (255, 255, 255, 255),
    )
    mask = Image.new("L", (badge_size, badge_size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, badge_size, badge_size), fill=255)

    badge_pos = (
        (canvas_size - badge_size) // 2,
        (canvas_size - badge_size) // 2,
    )
    canvas.paste(badge, badge_pos, mask)

    # logo
    if os.path.exists(LOGO):
        logo = Image.open(LOGO).convert("RGBA")
        logo_size = int(badge_size * 0.65)
        logo = logo.resize((logo_size, logo_size))

        logo_pos = (
            (canvas_size - logo_size) // 2,
            (canvas_size - logo_size) // 2,
        )
        canvas.paste(logo, logo_pos, logo)

    filepath = os.path.join(QR_FOLDER, f"{name}_qr.png")
    canvas.save(filepath, format="PNG", optimize=True)

    print(f"✅ QR premium créé : {filepath}")


# =========================================================
# 🚀 MAIN
# =========================================================
if __name__ == "__main__":
    for name, config in QR_CONFIGS.items():
        generate_premium_qr(
            name,
            config["route"],
            config["colors"],
        )

    print("🎉 QR codes premium COUD prêts.")