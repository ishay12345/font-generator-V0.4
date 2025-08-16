import os
import sys
import cv2
import numpy as np

def convert_image_to_bw(input_path, output_path):
    gray = cv2.imread(input_path, cv2.IMREAD_GRAYSCALE)
    if gray is None:
        print(f"❌ לא ניתן לטעון את התמונה: {input_path}")
        return False

    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    white_bg = np.sum(bw == 255)
    black_fg = np.sum(bw == 0)
    if black_fg > white_bg:
        bw = cv2.bitwise_not(bw)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cv2.imwrite(output_path, bw)
    print(f"✅ {input_path} → {output_path}")
    return True

def convert_to_bw(input_dir_or_file, output_dir_or_file):
    if os.path.isfile(input_dir_or_file):
        convert_image_to_bw(input_dir_or_file, output_dir_or_file)
    elif os.path.isdir(input_dir_or_file):
        os.makedirs(output_dir_or_file, exist_ok=True)
        for fname in os.listdir(input_dir_or_file):
            if fname.lower().endswith(".png"):
                convert_image_to_bw(
                    os.path.join(input_dir_or_file, fname),
                    os.path.join(output_dir_or_file, fname)
                )

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("שימוש: python bw_converter.py <input_path> <output_path>")
        sys.exit(1)

    convert_to_bw(sys.argv[1], sys.argv[2])
