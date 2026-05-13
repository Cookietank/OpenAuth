import os
from PIL import Image, ImageDraw

def generate_hd_ico():
    # 256x256 Transparent canvas
    image = Image.new('RGBA', (256, 256), color=(255, 255, 255, 0))
    draw = ImageDraw.Draw(image)

    # Draw the Blue Shield (Scaled up 4x)
    draw.polygon([
        (128, 16), (32, 64), (32, 160), 
        (128, 240), (224, 160), (224, 64)
    ], fill="#005A9E")
    
    # Draw the White Keyhole (Scaled up 4x)
    draw.ellipse([(104, 88), (152, 136)], fill="white")
    draw.polygon([(120, 128), (136, 128), (136, 192), (120, 192)], fill="white")

    # Ensure plugins directory exists
    os.makedirs("plugins", exist_ok=True)
    
    # Save it with multiple embedded sizes for Windows to use seamlessly
    icon_path = os.path.join("plugins", "icon.ico")
    image.save(icon_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
    print(f"✅ Successfully generated HD icon at: {icon_path}")

if __name__ == "__main__":
    generate_hd_ico()