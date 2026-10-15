import os
from PIL import Image, ImageDraw, ImageFont

# Set paths
assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
os.makedirs(assets_dir, exist_ok=True)

logo_path = os.path.join(assets_dir, "logo.png")
banner_path = os.path.join(assets_dir, "banner.png")

# 1. Generate Logo (150x150)
logo = Image.new("RGBA", (150, 150), (255, 255, 255, 0))
draw = ImageDraw.Draw(logo)
# Draw rounded card with gradient feel
draw.rounded_rectangle([10, 10, 140, 140], radius=30, fill=(79, 70, 229, 255))
# Draw simplified bar chart graphic inside logo
draw.rectangle([40, 95, 55, 115], fill=(255, 255, 255, 255))
draw.rectangle([65, 75, 80, 115], fill=(255, 255, 255, 255))
draw.rectangle([90, 50, 105, 115], fill=(16, 185, 129, 255))
logo.save(logo_path)
print(f"Logo created at {logo_path}")

# 2. Generate Banner (1200x400)
banner = Image.new("RGB", (1200, 400), (15, 23, 42)) # Slate dark bg
draw = ImageDraw.Draw(banner)
# Draw abstract shapes/gradients
for i in range(100):
    opacity = int(255 * (1 - i/100) * 0.15)
    draw.ellipse([200 - i*2, 200 - i*2, 200 + i*2, 200 + i*2], outline=(79, 70, 229, opacity), width=2)
    draw.ellipse([900 - i*2, 200 - i*2, 900 + i*2, 200 + i*2], outline=(6, 182, 212, opacity), width=2)
banner.save(banner_path)
print(f"Banner created at {banner_path}")
