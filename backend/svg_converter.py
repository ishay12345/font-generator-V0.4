import os
import subprocess
from PIL import Image

def convert_png_to_svg(input_path, output_path):
    """
    פונקציה לייבוא בקוד: ממירה PNG ל-SVG באמצעות Potrace.
    """
    bmp_path = input_path.replace(".png", ".bmp")
    Image.open(input_path).save(bmp_path)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        subprocess.run([
            "potrace", bmp_path,
            "--svg", "-o", output_path
        ], check=True)
        print(f"✅ {input_path} → {output_path}")
    except subprocess.CalledProcessError:
        print(f"❌ שגיאה בהמרת {input_path}")
    finally:
        if os.path.exists(bmp_path):
            os.remove(bmp_path)
    return output_path


def convert_to_svg(input_dir_or_file, output_dir_or_file):
    if os.path.isfile(input_dir_or_file):
        return convert_png_to_svg(input_dir_or_file, output_dir_or_file)
    elif os.path.isdir(input_dir_or_file):
        os.makedirs(output_dir_or_file, exist_ok=True)
        for fname in os.listdir(input_dir_or_file):
            if fname.lower().endswith(".png"):
                convert_png_to_svg(
                    os.path.join(input_dir_or_file, fname),
                    os.path.join(output_dir_or_file, fname.replace(".png", ".svg"))
                )


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("שימוש: python svg_converter.py <input_path> <output_path>")
        sys.exit(1)
    convert_to_svg(sys.argv[1], sys.argv[2])
