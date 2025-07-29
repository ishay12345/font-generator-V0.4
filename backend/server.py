from flask import Flask, request, render_template, send_file, url_for, redirect
import os
from split_letters import split_letters_from_image
from bw_converter import convert_to_bw
from svg_converter import convert_to_svg
from generate_font import generate_ttf

# תשלום
from create_payment import create_low_profile_payment
from urllib.parse import parse_qs

# ---- תיקיות עבודה ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
SPLIT_FOLDER  = os.path.join(BASE_DIR, 'split_letters_output')
BW_FOLDER     = os.path.join(BASE_DIR, 'bw_letters')
SVG_FOLDER    = os.path.join(BASE_DIR, 'svg_letters')
EXPORT_FOLDER = os.path.join(BASE_DIR, '..', 'exports')
FONT_OUTPUT_PATH = os.path.join(EXPORT_FOLDER, 'my_font.ttf')

# ודא שהתיקיות קיימות
for d in (UPLOAD_FOLDER, SPLIT_FOLDER, BW_FOLDER, SVG_FOLDER, EXPORT_FOLDER):
    os.makedirs(d, exist_ok=True)

# אתחול Flask עם תיקיית התבניות
TEMPLATE_DIR = os.path.join(BASE_DIR, '..', 'frontend', 'templates')
app = Flask(__name__, template_folder=TEMPLATE_DIR)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SPLIT_FOLDER']  = SPLIT_FOLDER
app.config['BW_FOLDER']     = BW_FOLDER
app.config['SVG_FOLDER']    = SVG_FOLDER


# ----------------------
# 🔠 דף הבית + העלאה
# ----------------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return render_template('index.html', error='לא נשלח קובץ')

    file = request.files['file']
    if file.filename == '':
        return render_template('index.html', error='לא נבחר קובץ')

    # שמירת התמונה
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    try:
        # שלב 1 – חיתוך
        split_letters_from_image(filepath, output_dir=SPLIT_FOLDER)

        # שלב 2 – המרה לשחור־לבן
        convert_to_bw(input_dir=SPLIT_FOLDER, output_dir=BW_FOLDER)

        # שלב 3 – המרה ל־SVG
        convert_to_svg(input_dir=BW_FOLDER, output_dir=SVG_FOLDER)

        # שלב 4 – יצירת פונט TTF
        font_created = generate_ttf(svg_folder=SVG_FOLDER, output_ttf=FONT_OUTPUT_PATH)

        # בדיקות
        cutting_done = len(os.listdir(SPLIT_FOLDER)) > 0
        bw_done      = len(os.listdir(BW_FOLDER)) > 0
        svg_done     = len(os.listdir(SVG_FOLDER)) > 0

        print(f"✂️ חיתוך אותיות:     {'הושלם' if cutting_done else 'נכשל'}")
        print(f"🖤 המרה לשחור־לבן:   {'הושלם' if bw_done else 'נכשל'}")
        print(f"🟢 המרה ל־SVG:      {'הושלם' if svg_done else 'נכשל'}")
        print(f"🔠 יצירת פונט:       {'הושלם' if font_created else 'נכשל'}")

        return render_template(
            'index.html',
            cutting_done=cutting_done,
            bw_done=bw_done,
            svg_done=svg_done,
            font_created=font_created
        )

    except Exception as e:
        print("❌ שגיאה בתהליך:", str(e))
        return render_template('index.html', error=f"שגיאה: {str(e)}")


@app.route('/download')
def download_font():
    if os.path.exists(FONT_OUTPUT_PATH):
        return send_file(
            FONT_OUTPUT_PATH,
            as_attachment=True,
            download_name='my_font.ttf',
            mimetype='font/ttf'
        )
    return render_template('index.html', error='הפונט לא קיים להורדה'), 404


# ----------------------
# 📄 דפי מידע
# ----------------------

@app.route('/instructions')
def instructions():
    return render_template('instructions.html')


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


# ----------------------
# 📬 Webhook – קבלת תוצאה מקרדקום
# ----------------------

@app.route('/cardcom-indicator', methods=['POST'])
def cardcom_indicator():
    data = request.form.to_dict()
    print("📬 קיבלנו הודעה מקרדקום:")
    for key, value in data.items():
        print(f"{key}: {value}")
    
    # לדוגמה – תוכל לבדוק אם OperationResponse == 0 כדי לדעת שהתשלום הצליח
    return "OK"
    

# ----------------------

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
