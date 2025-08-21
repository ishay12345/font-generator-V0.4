import os
import base64
import shutil
import requests
from flask import Flask, render_template, request, redirect, url_for, send_file, session
from werkzeug.utils import secure_filename
from urllib.parse import parse_qs
from email.message import EmailMessage
import smtplib

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
INVOICE_FOLDER = os.path.join(EXPORT_FOLDER, 'invoices')

for d in (UPLOADS_DIR, PROCESSED_DIR, GLYPHS_DIR, BW_DIR, SVG_DIR, EXPORT_FOLDER, INVOICE_FOLDER):
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

# דואר לשליחת חשבוניות
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_SERVER = "smtp.gmail.com"
EMAIL_PORT = 587

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
# 📤 העלאת תמונה
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

    bw_name = f"bw_{filename}"
    bw_path = os.path.join(PROCESSED_DIR, bw_name)
    convert_to_black_white(input_path, bw_path, filename=bw_name)

    processed_name = f"proc_{filename}"
    processed_path = os.path.join(PROCESSED_DIR, processed_name)
    normalize_and_center_glyph(input_path, processed_path, filename=processed_name)

    session['last_filename'] = processed_name
    return redirect(url_for('crop', filename=processed_name))

# ----------------------
# ✂️ דף חיתוך
# ----------------------
@app.route('/crop')
def crop():
    filename = request.args.get('filename') or session.get('last_filename')
    if not filename:
        return render_template('crop.html', error="אין תמונה זמינה לחיתוך")

    path_check = os.path.join(UPLOADS_DIR, filename)
    if not os.path.exists(path_check):
        return render_template('crop.html', error="התמונה המבוקשת לא נמצאה בדיסק")

    font_ready = session.get('font_ready', os.path.exists(FONT_OUTPUT_PATH))
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

        return {"saved": f"{eng_name}.png"}
    except Exception as e:
        return {"error": str(e)}, 500

# ----------------------
# 🔠 יצירת פונט
# ----------------------
@app.route('/generate_font', methods=['POST'])
def generate_font_route():
    try:
        generate_ttf(svg_folder=SVG_DIR, output_ttf=FONT_OUTPUT_PATH)

        if os.path.exists(FONT_OUTPUT_PATH):
            session['font_ready'] = True
            return jsonify({
                "status": "success",
                "download_url": url_for('download_page')
            })
        else:
            session['font_ready'] = False
            return jsonify({
                "status": "error",
                "message": "❌ הפונט לא נוצר."
            })

    except Exception as e:
        session['font_ready'] = False
        return jsonify({
            "status": "error",
            "message": f"❌ שגיאה: {str(e)}"
        })

# ----------------------
# ⬇️ הורדת פונט
# ----------------------
@app.route('/download')
def download_page():
    if not session.get("paid"):
        return redirect(url_for('payment'))

    font_ready = session.get('font_ready', os.path.exists(FONT_OUTPUT_PATH))
    if not font_ready:
        return redirect(url_for('index'))

    font_url = url_for('download_font')
    return render_template('downloadd.html', font_url=font_url)

@app.route('/download_font')
def download_font():
    if not session.get("paid"):
        return redirect(url_for('payment'))

    if os.path.exists(FONT_OUTPUT_PATH):
        return send_file(FONT_OUTPUT_PATH, as_attachment=True, download_name="my_font.ttf", mimetype="font/ttf")
    return "הפונט עדיין לא נוצר", 404

# ----------------------
# 💳 תשלום – קארדקום
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

    payload = {
        "TerminalNumber": CARD_COM_TERMINAL,
        "UserName": CARD_COM_USER,
        "APILevel": "10",
        "Operation": "1",  # חיוב רגיל
        "Language": "he",
        "CoinID": "1",
        "SumToBill": "1.00",
        "ProductName": "פונט אישי",
        "SuccessRedirectUrl": request.host_url + "thankyou",
        "ErrorRedirectUrl": request.host_url + "payment",
        "IndicatorUrl": request.host_url + "cardcom-indicator",
        "CustomerEmail": email,
        "CustomerName": name,
    }

    try:
        resp = requests.post(CARD_COM_API_URL, data=payload)
        result = parse_qs(resp.text)
        redirect_url = result.get("url", [None])[0]
        if redirect_url:
            session["customer_email"] = email
            session["customer_name"] = name
            return redirect(redirect_url)
        else:
            return f"שגיאה: {resp.text}", 500
    except Exception as e:
        return f"שגיאה בעת יצירת התשלום: {str(e)}", 500

@app.route('/cardcom-indicator', methods=['GET', 'POST'])
def cardcom_indicator():
    data = request.form.to_dict() if request.method == 'POST' else request.args.to_dict()

    if data.get("OperationResponse") == "0":  # תשלום הצליח
        session["paid"] = True
        # שליחת חשבונית אוטומטית
        send_invoice(session.get("customer_email"), session.get("customer_name"))
    else:
        session["paid"] = False

    return "OK"

@app.route('/thankyou')
def thankyou():
    return render_template('thankyou.html')

# ----------------------
# 📄 דפים נוספים
# ----------------------
@app.route('/instructions')
def instructions():
    return render_template('instructions.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

# ----------------------
# 📧 שליחת חשבונית
# ----------------------
def send_invoice(email, name):
    try:
        invoice_path = os.path.join(INVOICE_FOLDER, f"invoice_{name}.pdf")
        # כאן ניתן ליצור PDF עם ספריית ReportLab או אחרת, כרגע יוצרים קובץ Placeholder
        with open(invoice_path, "wb") as f:
            f.write(b"%PDF-1.4\n% Placeholder invoice")

        msg = EmailMessage()
        msg['Subject'] = "חשבונית עבור הפונט האישי שלך"
        msg['From'] = EMAIL_USER
        msg['To'] = email
        msg.set_content(f"שלום {name},\n\nתודה על הרכישה! מצורפת החשבונית.\n\n-- צוות הפונט")
        with open(invoice_path, "rb") as f:
            msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename=os.path.basename(invoice_path))

        with smtplib.SMTP(EMAIL_SERVER, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"[send_invoice] ✅ חשבונית נשלחה ל-{email}")
    except Exception as e:
        print(f"[send_invoice] ❌ שגיאה בשליחת חשבונית: {e}")

# ----------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
