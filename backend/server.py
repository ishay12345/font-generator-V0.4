import os
import base64
import shutil
from flask import Flask, render_template, request, redirect, url_for, send_file, session, jsonify
from werkzeug.utils import secure_filename

# פונקציות עיבוד
from process_image import convert_to_black_white, normalize_and_center_glyph
from generate_font import generate_ttf
from svg_converter import convert_png_to_svg
from bw_converter import convert_to_bw

# תשלום
from create_payment import create_low_profile_payment
from urllib.parse import parse_qs

# --- נתיבי בסיס ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, '..', 'frontend', 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

# תיקיות עבודה
UPLOADS_DIR   = os.path.join(STATIC_DIR, 'uploads')
PROCESSED_DIR = os.path.join(STATIC_DIR, 'processed')
GLYPHS_DIR    = os.path.join(STATIC_DIR, 'glyphs')
BW_DIR        = os.path.join(STATIC_DIR, 'bw')
SVG_DIR       = os.path.join(STATIC_DIR, 'svg_letters')
EXPORT_FOLDER = os.path.join(BASE_DIR, '..', 'exports')
FONT_OUTPUT_PATH = os.path.join(EXPORT_FOLDER, 'my_font.ttf')

for d in (UPLOADS_DIR, PROCESSED_DIR, GLYPHS_DIR, BW_DIR, SVG_DIR, EXPORT_FOLDER):
    os.makedirs(d, exist_ok=True)

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')  # session

# סדר האותיות
LETTERS_ORDER = [
    "alef","bet","gimel","dalet","he","vav","zayin","het","tet",
    "yod","kaf","lamed","mem","nun","samekh","ayin","pe","tsadi",
    "qof","resh","shin","tav","finalkaf","finalmem","finalnun",
    "finalpe","finaltsadi"
]

# ----------------------
# 🔠 דף הבית
# ----------------------
@app.route('/')
def index():
    font_ready = session.get('font_ready', os.path.exists(FONT_OUTPUT_PATH))
    print(f"[index] font_ready: {font_ready}")
    return render_template('index.html', font_ready=font_ready)

# ----------------------
# 📤 העלאת תמונה → POST בלבד
# ----------------------
@app.route('/upload', methods=['POST'])
def upload():
    print("[upload] received upload request")
    if 'image' not in request.files:
        print("[upload] no image part in request")
        return render_template('index.html', error='לא נשלח קובץ')

    f = request.files['image']
    if f.filename == '':
        print("[upload] no filename")
        return render_template('index.html', error='לא נבחר קובץ')

    filename = secure_filename(f.filename)
    input_path = os.path.join(UPLOADS_DIR, filename)
    f.save(input_path)
    print(f"[upload] saved uploaded file: {filename}")

    # גרסה ראשונה: שמירה פשוטה (convert_to_black_white)
    bw_name = f"bw_{filename}"
    bw_path = os.path.join(PROCESSED_DIR, bw_name)
    convert_to_black_white(input_path, bw_path, filename=bw_name)
    print(f"[upload] converted to BW: {bw_name}")

    # גרסה שנייה: מנורמלת + ממורכזת
    processed_name = f"proc_{filename}"
    processed_path = os.path.join(PROCESSED_DIR, processed_name)
    normalize_and_center_glyph(input_path, processed_path, filename=processed_name)
    print(f"[upload] normalized and centered: {processed_name}")

    session['last_filename'] = processed_name
    print(f"[upload] session updated with last_filename: {processed_name}")

    # redirect ל-crop עם הגרסה המנורמלת
    return redirect(url_for('crop', filename=processed_name))

# ----------------------
# ✂️ דף חיתוך ידני
# ----------------------
@app.route('/crop')
def crop():
    filename = request.args.get('filename') or session.get('last_filename')
    print(f"[crop] requested filename: {filename}")

    if not filename:
        print("[crop] no filename available")
        return render_template('crop.html', error="אין תמונה זמינה לחיתוך")

    path_check = os.path.join(UPLOADS_DIR, filename)
    if not os.path.exists(path_check):
        print(f"[crop] file not found on disk: {filename}")
        return render_template('crop.html', error="התמונה המבוקשת לא נמצאה בדיסק")

    font_ready = session.get('font_ready', os.path.exists(FONT_OUTPUT_PATH))
    print(f"[crop] font_ready: {font_ready}")
    return render_template('crop.html', filename=filename, font_ready=font_ready)

# ----------------------
# ✂️ שמירת אות חתוכה
# ----------------------
@app.route('/backend/save_crop', methods=['POST'])
def save_crop():
    try:
        data = request.get_json()
        if not data:
            print("[save_crop] no JSON received")
            return jsonify({"error": "no json"}), 400

        index = data.get('index')
        imageData = data.get('data')

        if index is None or imageData is None:
            print("[save_crop] missing fields")
            return jsonify({"error": "missing fields"}), 400

        index = int(index)
        eng_name = LETTERS_ORDER[index]
        print(f"[save_crop] saving glyph: {eng_name}")

        _, b64 = imageData.split(',', 1)
        binary = base64.b64decode(b64)
        tmp_path = os.path.join(PROCESSED_DIR, f"tmp_{eng_name}.png")
        with open(tmp_path, 'wb') as fh:
            fh.write(binary)
        print(f"[save_crop] tmp PNG saved: {tmp_path}")

        # שמירה ל־glyphs
        out_path = os.path.join(GLYPHS_DIR, f"{eng_name}.png")
        shutil.copy(tmp_path, out_path)
        print(f"[save_crop] copied to glyphs: {out_path}")

        # שמירה ל־BW
        bw_out = os.path.join(BW_DIR, f"{eng_name}.png")
        shutil.copy(tmp_path, bw_out)
        print(f"[save_crop] copied to BW: {bw_out}")

        # המרה ל־SVG
        svg_out = os.path.join(SVG_DIR, f"{eng_name}.svg")
        convert_png_to_svg(bw_out, svg_out)
        print(f"[save_crop] converted to SVG: {svg_out}")

        return jsonify({"saved": f"{eng_name}.png"})
    except Exception as e:
        print(f"[save_crop] exception: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------------
# 🔠 יצירת פונט – JSON response
# ----------------------
@app.route('/generate_font', methods=['POST'])
def generate_font_route():
    try:
        print("[generate_font] generating TTF...")
        generate_ttf(svg_folder=SVG_DIR, output_ttf=FONT_OUTPUT_PATH)
        if os.path.exists(FONT_OUTPUT_PATH):
            session['font_ready'] = True
            print("[generate_font] font generated successfully")
            return jsonify({
                "status": "success",
                "message": "🎉 הפונט מוכן!",
                "download_url": url_for('download_page')
            })
        else:
            session['font_ready'] = False
            print("[generate_font] font not created")
            return jsonify({"status": "error", "message": "❌ הפונט לא נוצר. נסה שנית."}), 500
    except Exception as e:
        session['font_ready'] = False
        print(f"[generate_font] exception: {e}")
        return jsonify({"status": "error", "message": f"❌ שגיאה ביצירת הפונט: {e}"}), 500

# ----------------------
# ⬇️ דף download.html עם כפתור מעוצב
# ----------------------
@app.route('/downloadd')
def download_page():
    font_ready = session.get('font_ready', os.path.exists(FONT_OUTPUT_PATH))
    print(f"[download_page] font_ready: {font_ready}")
    if not font_ready:
        return redirect(url_for('index'))

    font_url = url_for('download_font')
    return render_template('downloadd.html', font_url=font_url)

# ----------------------
# ⬇️ הורדת פונט
# ----------------------
@app.route('/download_font')
def download_font():
    if os.path.exists(FONT_OUTPUT_PATH):
        print(f"[download_font] sending font: {FONT_OUTPUT_PATH}")
        return send_file(FONT_OUTPUT_PATH, as_attachment=True, download_name="my_font.ttf", mimetype="font/ttf")
    print("[download_font] font not ready")
    return "הפונט עדיין לא נוצר", 404

# ----------------------
# דפי מידע ותשלום
# ----------------------
@app.route('/instructions')
def instructions():
    print("[instructions] page loaded")
    return render_template('instructions.html')

@app.route('/faq')
def faq():
    print("[faq] page loaded")
    return render_template('faq.html')

@app.route('/payment')
def payment():
    print("[payment] page loaded")
    return render_template('payment.html')

@app.route("/start-payment", methods=["POST"])
def start_payment():
    email = request.form.get("email")
    name = request.form.get("name") or "לקוח ללא שם"
    print(f"[start_payment] email: {email}, name: {name}")

    if not email:
        return "יש להזין כתובת מייל", 400

    try:
        payment_response = create_low_profile_payment(customer_email=email, customer_name=name)
        result = parse_qs(payment_response)
        redirect_url = result.get("url", [None])[0]

        if redirect_url:
            print(f"[start_payment] redirecting to: {redirect_url}")
            return redirect(redirect_url)
        else:
            print("[start_payment] no redirect URL received")
            return "לא התקבלה כתובת URL מתאימה", 500
    except Exception as e:
        print(f"[start_payment] exception: {e}")
        return f"שגיאה בעת יצירת התשלום: {str(e)}", 500

@app.route('/cardcom-indicator', methods=['GET', 'POST'])
def cardcom_indicator():
    print("📬 קיבלנו הודעה מקרדקום:")
    print("🔹 שיטה:", request.method)
    data = request.form.to_dict() if request.method == 'POST' else request.args.to_dict()
    for key, value in data.items():
        print(f"{key}: {value}")
    return "OK"

@app.route('/thankyou')
def thankyou():
    print("[thankyou] page loaded")
    return render_template('thankyou.html')

# ----------------------
if __name__ == '__main__':
    print("[server] starting Flask app...")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
