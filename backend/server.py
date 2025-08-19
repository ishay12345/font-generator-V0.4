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
    return render_template('index.html', font_ready=font_ready)

# ----------------------
# 📤 העלאת תמונה → POST בלבד
# ----------------------
@app.route('/upload', methods=['POST'])
def upload():
    if 'image' not in request.files:
        return render_template('index.html', error='לא נשלח קובץ')

    f = request.files['image']
    if f.filename == '':
        return render_template('index.html', error='לא נבחר קובץ')

    filename = secure_filename(f.filename)
    input_path = os.path.join(UPLOADS_DIR, filename)
    f.save(input_path)

    # גרסה ראשונה: שמירה פשוטה (convert_to_black_white)
    bw_name = f"bw_{filename}"
    bw_path = os.path.join(PROCESSED_DIR, bw_name)
    convert_to_black_white(input_path, bw_path, filename=bw_name)

    # גרסה שנייה: מנורמלת + ממורכזת
    processed_name = f"proc_{filename}"
    processed_path = os.path.join(PROCESSED_DIR, processed_name)
    normalize_and_center_glyph(input_path, processed_path, filename=processed_name)

    session['last_filename'] = processed_name
    print(f"[upload] saved bw -> {bw_name}, normalized -> {processed_name}")

    # redirect ל-crop עם הגרסה המנורמלת
    return redirect(url_for('crop', filename=processed_name))

# ----------------------
# ✂️ דף חיתוך ידני
# ----------------------
@app.route('/crop')
def crop():
    filename = request.args.get('filename') or session.get('last_filename')

    if not filename:
        return render_template('crop.html', error="אין תמונה זמינה לחיתוך")

    path_check = os.path.join(UPLOADS_DIR, filename)
    if not os.path.exists(path_check):
        return render_template('crop.html', error="התמונה המבוקשת לא נמצאה בדיסק")

    return render_template('crop.html', filename=filename, font_ready=session.get('font_ready', os.path.exists(FONT_OUTPUT_PATH)))

# ----------------------
# ✂️ שמירת אות חתוכה
# ----------------------
@app.route('/backend/save_crop', methods=['POST'])
def save_crop():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "no json"}), 400

        index = data.get('index')
        imageData = data.get('data')

        if index is None or imageData is None:
            return jsonify({"error": "missing fields"}), 400

        index = int(index)
        eng_name = LETTERS_ORDER[index]

        _, b64 = imageData.split(',', 1)
        binary = base64.b64decode(b64)
        tmp_path = os.path.join(PROCESSED_DIR, f"tmp_{eng_name}.png")
        with open(tmp_path, 'wb') as fh:
            fh.write(binary)

        # שמירה ל־glyphs
        out_path = os.path.join(GLYPHS_DIR, f"{eng_name}.png")
        shutil.copy(tmp_path, out_path)

        # שמירה ל־BW
        bw_out = os.path.join(BW_DIR, f"{eng_name}.png")
        shutil.copy(tmp_path, bw_out)

        # המרה ל־SVG
        svg_out = os.path.join(SVG_DIR, f"{eng_name}.svg")
        convert_png_to_svg(bw_out, svg_out)

        return jsonify({"saved": f"{eng_name}.png"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----------------------
# 🔠 יצירת פונט – JSON response
# ----------------------
@app.route('/generate_font', methods=['POST'])
def generate_font_route():
    try:
        generate_ttf(svg_folder=SVG_DIR, output_ttf=FONT_OUTPUT_PATH)
        if os.path.exists(FONT_OUTPUT_PATH):
            session['font_ready'] = True
            return jsonify({
                "status": "success",
                "message": "🎉 הפונט מוכן!",
                "download_url": url_for('download_page')
            })
        else:
            session['font_ready'] = False
            return jsonify({"status": "error", "message": "❌ הפונט לא נוצר. נסה שנית."}), 500
    except Exception as e:
        session['font_ready'] = False
        return jsonify({"status": "error", "message": f"❌ שגיאה ביצירת הפונט: {e}"}), 500

# ----------------------
# ⬇️ דף download.html עם כפתור מעוצב
# ----------------------
@app.route('/download')
def download_page():
    if not session.get('font_ready', os.path.exists(FONT_OUTPUT_PATH)):
        return redirect(url_for('index'))

    # ניתן להעביר כתובת הפונט דרך GET
    font_url = url_for('download_font')
    return render_template('download.html', font_url=font_url)

# ----------------------
# ⬇️ הורדת פונט
# ----------------------
@app.route('/download_font')
def download_font():
    if os.path.exists(FONT_OUTPUT_PATH):
        return send_file(FONT_OUTPUT_PATH, as_attachment=True, download_name="my_font.ttf", mimetype="font/ttf")
    return "הפונט עדיין לא נוצר", 404

# ----------------------
# דפי מידע ותשלום
# ----------------------
@app.route('/instructions')
def instructions():
    return render_template('instructions.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/payment')
def payment():
    return render_template('payment.html')

@app.route("/start-payment", methods=["POST"])
def start_payment():
    email = request.form.get("email")
    name = request.form.get("name") or "לקוח ללא שם"

    if not email:
        return "יש להזין כתובת מייל", 400

    try:
        payment_response = create_low_profile_payment(customer_email=email, customer_name=name)
        result = parse_qs(payment_response)
        redirect_url = result.get("url", [None])[0]

        if redirect_url:
            return redirect(redirect_url)
        else:
            return "לא התקבלה כתובת URL מתאימה", 500
    except Exception as e:
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
    return render_template('thankyou.html')

# ----------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
