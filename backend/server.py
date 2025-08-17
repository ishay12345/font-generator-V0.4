import os
import base64
import shutil
from flask import Flask, render_template, request, jsonify, url_for, send_file, redirect, session
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
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')  # עבור session

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
    font_ready = os.path.exists(FONT_OUTPUT_PATH)
    return render_template('index.html', font_ready=font_ready)

# ----------------------
# 📤 העלאת תמונה → חיתוך ידני
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

    # --- גרסה ראשונה: שמירה פשוטה (convert_to_black_white) ---
    bw_name = f"bw_{filename}"
    bw_path = os.path.join(PROCESSED_DIR, bw_name)
    convert_to_black_white(input_path, bw_path, filename=bw_name)

    # --- גרסה שנייה: מנורמלת + ממורכזת ---
    processed_name = f"proc_{filename}"
    processed_path = os.path.join(PROCESSED_DIR, processed_name)
    normalize_and_center_glyph(input_path, processed_path, filename=processed_name)

    # נעדיף להמשיך עם הגרסה המנורמלת
    session['last_filename'] = processed_name
    print(f"[upload] saved bw -> {bw_name}, normalized -> {processed_name}")

    # redirect ל-crop עם הגרסה המנורמלת
    return redirect(url_for('crop', filename=processed_name))

# ----------------------
# ✂️ דף חיתוך ידני (עם נפילה-אחורית אם חסר filename)
# ----------------------
@app.route('/crop')
def crop():
    filename = request.args.get('filename')

    # אם אין בפרמטרים – ננסה מה-session
    if not filename:
        filename = session.get('last_filename')

    # אם עדיין אין – ננסה לבחור את הקובץ המעובד האחרון מתיקיית uploads
    if not filename:
        try:
            candidates = [
                f for f in os.listdir(UPLOADS_DIR)
                if os.path.isfile(os.path.join(UPLOADS_DIR, f)) and f.startswith('proc_')
            ]
            if candidates:
                # לבחור את האחרון לפי זמן שינוי
                candidates.sort(key=lambda n: os.path.getmtime(os.path.join(UPLOADS_DIR, n)), reverse=True)
                filename = candidates[0]
                session['last_filename'] = filename
                print(f"[crop] fallback picked latest processed: {filename}")
        except Exception as e:
            print(f"[crop] fallback scan error: {e}")

    if not filename:
        # אין מה להציג
        return render_template('crop.html', error="אין תמונה זמינה לחיתוך")

    # יש קובץ – לוודא שהוא באמת קיים ב-static/uploads
    path_check = os.path.join(UPLOADS_DIR, filename)
    if not os.path.exists(path_check):
        print(f"[crop] requested filename not found on disk: {filename}")
        return render_template('crop.html', error="התמונה המבוקשת לא נמצאה בדיסק")

    return render_template('crop.html', filename=filename, font_ready=os.path.exists(FONT_OUTPUT_PATH))

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

        # המרה מבסיס64 ל־PNG
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
# 🔠 יצירת פונט
# ----------------------
@app.route('/generate_font', methods=['POST'])
def generate_font_route():
    try:
        success, _ = generate_ttf(svg_folder=SVG_DIR, output_ttf=FONT_OUTPUT_PATH)
        if success:
            return redirect(url_for('index'))
        else:
            return render_template('index.html', error='כישלון ביצירת הפונט')
    except Exception as e:
        return render_template('index.html', error=str(e))

# ----------------------
# ⬇️ הורדת פונט
# ----------------------
@app.route('/download_font')
def download_font():
    if os.path.exists(FONT_OUTPUT_PATH):
        return send_file(FONT_OUTPUT_PATH, as_attachment=True, download_name="my_font.ttf", mimetype="font/ttf")
    return "הפונט עדיין לא נוצר", 404

# ----------------------
# 📄 דפי מידע
# ----------------------
@app.route('/instructions')
def instructions():
    return render_template('instructions.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

# ----------------------
# 💳 תשלום
# ----------------------
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
