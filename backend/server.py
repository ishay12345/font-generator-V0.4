import os
import base64
import shutil
import requests
from flask import Flask, render_template, request, redirect, url_for, send_file, session, jsonify
from werkzeug.utils import secure_filename
from urllib.parse import parse_qs

# פונקציות עיבוד
from process_image import convert_to_black_white, normalize_and_center_glyph
from generate_font import generate_ttf
from svg_converter import convert_png_to_svg
from bw_converter import convert_to_bw

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

# ----------------------
# 📌 פרטי קארדקום
# ----------------------
CARD_COM_TERMINAL = "172726"
CARD_COM_USER = "4cbscU43zRCYzL9YLSxV"
CARD_COM_PASSWORD = "vTPYaAqgqFawtfbBrOOI"
CARD_COM_API_URL = "https://secure.cardcom.solutions/Interface/LowProfile.aspx"

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
    print(f"[index] האם הפונט מוכן? {font_ready}")
    return render_template('index.html', font_ready=font_ready)

# ----------------------
# 📤 העלאת תמונה
# ----------------------
@app.route('/upload', methods=['POST'])
def upload():
    if 'image' not in request.files:
        print("[upload] נכשל – לא התקבל קובץ")
        return render_template('index.html', error='לא נשלח קובץ')

    f = request.files['image']
    if f.filename == '':
        print("[upload] נכשל – לא נבחר קובץ")
        return render_template('index.html', error='לא נבחר קובץ')

    filename = secure_filename(f.filename)
    input_path = os.path.join(UPLOADS_DIR, filename)
    f.save(input_path)
    print(f"[upload] הקובץ {filename} נשמר בהצלחה")

    bw_name = f"bw_{filename}"
    bw_path = os.path.join(PROCESSED_DIR, bw_name)
    convert_to_black_white(input_path, bw_path, filename=bw_name)
    print(f"[upload] נוצר קובץ שחור-לבן: {bw_name}")

    processed_name = f"proc_{filename}"
    processed_path = os.path.join(PROCESSED_DIR, processed_name)
    normalize_and_center_glyph(input_path, processed_path, filename=processed_name)
    print(f"[upload] נוצר קובץ מעובד: {processed_name}")

    session['last_filename'] = processed_name
    return redirect(url_for('crop', filename=processed_name))


# ✂️ דף חיתוך
# ----------------------
@app.route('/crop')
def crop():
    filename = request.args.get('filename') or session.get('last_filename')
    if not filename:
        print("[crop] אין תמונה זמינה לחיתוך")
        return render_template('crop.html', error="אין תמונה זמינה לחיתוך")

    path_check = os.path.join(UPLOADS_DIR, filename)
    if not os.path.exists(path_check):
        print(f"[crop] התמונה {filename} לא נמצאה בדיסק")
        return render_template('crop.html', error="התמונה המבוקשת לא נמצאה בדיסק")

    font_ready = session.get('font_ready', os.path.exists(FONT_OUTPUT_PATH))
    print(f"[crop] טוען עמוד חיתוך עבור {filename}, פונט מוכן? {font_ready}")
    return render_template('crop.html', filename=filename, font_ready=font_ready)

# ----------------------
# ✂️ שמירת אות חתוכה
# ----------------------
@app.route('/backend/save_crop', methods=['POST'])
def save_crop():
    try:
        data = request.get_json()
        index = int(data.get('index'))
        eng_name = LETTERS_ORDER[index]

        _, b64 = data.get('data').split(',', 1)
        binary = base64.b64decode(b64)
        tmp_path = os.path.join(PROCESSED_DIR, f"tmp_{eng_name}.png")
        with open(tmp_path, 'wb') as fh:
            fh.write(binary)

        out_path = os.path.join(GLYPHS_DIR, f"{eng_name}.png")
        shutil.copy(tmp_path, out_path)

        bw_out = os.path.join(BW_DIR, f"{eng_name}.png")
        shutil.copy(tmp_path, bw_out)

        svg_out = os.path.join(SVG_DIR, f"{eng_name}.svg")
        convert_png_to_svg(bw_out, svg_out)

        print(f"[save_crop] האות {eng_name} נשמרה בהצלחה")
        return jsonify({"saved": f"{eng_name}.png"})
    except Exception as e:
        print(f"[save_crop] שגיאה: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------------
# 🔠 יצירת פונט
# ----------------------
@app.route('/generate_font', methods=['POST'])
def generate_font_route():
    try:
        print("[generate_font] התחלת יצירת פונט...")
        generate_ttf(svg_folder=SVG_DIR, output_ttf=FONT_OUTPUT_PATH)
        if os.path.exists(FONT_OUTPUT_PATH):
            session['font_ready'] = True
            print("[generate_font] 🎉 הפונט נוצר בהצלחה!")
            return jsonify({
                "status": "success",
                "message": "🎉 הפונט מוכן!",
                "download_url": url_for('download_page')
            })
        else:
            session['font_ready'] = False
            print("[generate_font] ❌ הפונט לא נוצר")
            return jsonify({"status": "error", "message": "❌ הפונט לא נוצר."}), 500
    except Exception as e:
        session['font_ready'] = False
        print(f"[generate_font] ❌ שגיאה: {e}")
        return jsonify({"status": "error", "message": f"❌ שגיאה: {e}"}), 500

# ----------------------
# ⬇️ הורדת פונט
# ----------------------
@app.route('/download')
def download_page():
    font_ready = session.get('font_ready', os.path.exists(FONT_OUTPUT_PATH))
    print(f"[download_page] טוען עמוד הורדה – פונט מוכן? {font_ready}")
    if not font_ready:
        return redirect(url_for('index'))

    font_url = url_for('download_font')
    return render_template('downloadd.html', font_url=font_url)

@app.route('/download_font')
def download_font():
    if os.path.exists(FONT_OUTPUT_PATH):
        print("[download_font] שולח קובץ פונט להורדה")
        return send_file(FONT_OUTPUT_PATH, as_attachment=True, download_name="my_font.ttf", mimetype="font/ttf")
    print("[download_font] ❌ הפונט עדיין לא נוצר")
    return "הפונט עדיין לא נוצר", 404

# ----------------------
# 💳 תשלום – קארדקום
# ----------------------
@app.route('/payment')
def payment():
    print("[payment] עמוד תשלום נטען")
    return render_template('payment.html')

@app.route("/start-payment", methods=["POST"])
def start_payment():
    email = request.form.get("email")
    name = request.form.get("name") or "לקוח ללא שם"

    print(f"[start_payment] התחלת תשלום עבור {name}, אימייל: {email}")

    if not email:
        print("[start_payment] נכשל – לא הוזן מייל")
        return "יש להזין כתובת מייל", 400

    payload = {
        "TerminalNumber": CARD_COM_TERMINAL,
        "UserName": CARD_COM_USER,
        "APILevel": "10",
        "Operation": "1",  # חיוב רגיל
        "Language": "he",
        "CoinID": "1",  # שקל
        "SumToBill": "1.00",  # 💰 כאן משנים את המחיר
        "ProductName": "פונט אישי",
        "SuccessRedirectUrl": request.host_url + "thankyou",
        "ErrorRedirectUrl": request.host_url + "payment",
        "IndicatorUrl": request.host_url + "cardcom-indicator",
        "CustomerEmail": email,
        "CustomerName": name,
    }

    print(f"[start_payment] שולח בקשה ל-CardCom עם נתונים: {payload}")

    try:
        resp = requests.post(CARD_COM_API_URL, data=payload)
        print(f"[start_payment] תגובת CardCom: {resp.text}")

        result = parse_qs(resp.text)
        redirect_url = result.get("url", [None])[0]

        if redirect_url:
            print(f"[start_payment] הפניה לכתובת: {redirect_url}")
            return redirect(redirect_url)
        else:
            print("[start_payment] ❌ שגיאה – לא התקבל URL מהשרת")
            return f"שגיאה: {resp.text}", 500
    except Exception as e:
        print(f"[start_payment] ❌ חריגה: {e}")
        return f"שגיאה בעת יצירת התשלום: {str(e)}", 500

@app.route('/cardcom-indicator', methods=['GET', 'POST'])
def cardcom_indicator():
    data = request.form.to_dict() if request.method == 'POST' else request.args.to_dict()
    print("📬 CardCom Indicator:", data)
    return "OK"

@app.route('/thankyou')
def thankyou():
    print("[thankyou] עמוד תודה נטען")
    return render_template('thankyou.html')

# ----------------------
# 📄 דפים חדשים
# ----------------------
@app.route('/instructions')
def instructions():
    print("[instructions] עמוד הוראות נטען")
    return render_template('instructions.html')

@app.route('/faq')
def faq():
    print("[faq] עמוד שאלות נפוצות נטען")
    return render_template('faq.html')

# ----------------------
if __name__ == '__main__':
    print("[server] 🚀 Flask app מתחיל לרוץ...")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
