import os
import cv2
import numpy as np
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def convert_to_black_white(input_path, output_path, filename=None):
    """
    קורא את התמונה כמו שהיא, רק שומר או מעבד במידת הצורך (כאן לא משנה צבע).
    """
    img = cv2.imread(input_path)
    if img is None:
        raise ValueError(f"Cannot read image: {input_path}")

    # שמירה ישירה בלי המרה
    cv2.imwrite(output_path, img)
    print(f"[OK] Image saved without BW conversion to: {output_path}")

    if filename:
        static_uploads = os.path.join(BASE_DIR, 'static', 'uploads')
        os.makedirs(static_uploads, exist_ok=True)
        shutil.copy(output_path, os.path.join(static_uploads, filename))
        print(f"[OK] Copied to static/uploads/{filename}")

    return output_path



def normalize_and_center_glyph(input_path, output_path, filename=None, target_size=600, margin=50, vertical_offset=0):
    """
    מנרמל ומרכז את התמונה בצבע המקורי בלי המרה לשחור-לבן.
    """
    img = cv2.imread(input_path)
    if img is None:
        raise ValueError(f"Cannot read image: {input_path}")

    h, w = img.shape[:2]

    max_dim = target_size - 2 * margin
    scale = min(max_dim / w, max_dim / h)
    new_w, new_h = int(w * scale), int(h * scale)

    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    canvas = 255 * np.ones((target_size, target_size, 3), dtype=np.uint8)  # לבן RGB

    x_off = (target_size - new_w) // 2
    y_off = (target_size - new_h) // 2 + vertical_offset

    canvas[y_off:y_off+new_h, x_off:x_off+new_w] = resized

    cv2.imwrite(output_path, canvas)
    print(f"[OK] Normalized color glyph saved to: {output_path}")

    if filename:
        static_uploads = os.path.join(BASE_DIR, 'static', 'uploads')
        os.makedirs(static_uploads, exist_ok=True)
        shutil.copy(output_path, os.path.join(static_uploads, filename))
        print(f"[OK] Copied to static/uploads/{filename}")

    return output_path
