# backend/payment_webhook.py

from flask import Blueprint, request, jsonify
import urllib.parse
import datetime

webhook = Blueprint('webhook', __name__)

@webhook.route("/cardcom-indicator", methods=["POST"])
def cardcom_indicator():
    """
    נקודת קבלה של Webhook (IndicatorUrl) מ־Cardcom.
    מחזירה מידע על סטטוס עסקה: הצליחה/נכשלה, ופרטי לקוח.
    """

    # קריאת פרמטרים מה־POST (הם מגיעים כ־application/x-www-form-urlencoded)
    try:
        data = urllib.parse.parse_qs(request.get_data(as_text=True))
        operation_response = data.get("OperationResponse", [""])[0]
        low_profile_code = data.get("LowProfileCode", [""])[0]
        client_email = data.get("Email", [""])[0]
        invoice_number = data.get("InvoiceResponse.InvoiceNumber", [""])[0]

        # אפשר גם להוציא שם לקוח, תאריך עסקה, סכום וכו'
        amount = data.get("Sum", [""])[0]

        # תיעוד – לצורך בדיקה
        print("💬 התקבלה הודעה מקארדקום:")
        print("תוצאה:", operation_response)
        print("אסימון עסקה:", low_profile_code)
        print("מייל לקוח:", client_email)
        print("חשבונית #:", invoice_number)
        print("סכום:", amount)

        # טיפול לפי הצלחה או כישלון
        if operation_response == "0":
            print("✅ עסקה בוצעה בהצלחה")
            # כאן אפשר לשמור במסד נתונים, להפעיל פונקציה נוספת, לשלוח מייל וכו'
        else:
            print("❌ העסקה נכשלה או בוטלה")

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print("שגיאה בטיפול ב־Webhook:", str(e))
        return jsonify({"error": str(e)}), 500
