import requests
import urllib.parse

# קונפיגורציה – מזהה ספק שלך וכו'
CARDCOM_TERMINAL_NUMBER = "172726"  # תחליף במספר טרמינל שלך
CARDCOM_USER_NAME = "4cbscU43zRCYzL9YLSxV"  # מייל או שם משתמש
CARDCOM_LOW_PROFILE_URL = "https://secure.cardcom.solutions/Interface/LowProfile.aspx"

# כתובת חזרה אוטומטית אחרי תשלום (שינוי במידת הצורך)
SUCCESS_RETURN_URL = "https://myfont.co.il/download"  # הורדת הפונט לאחר תשלום
ERROR_RETURN_URL = "https://myfont.co.il/payment?status=failed"

# פונקציה: יצירת תשלום + בקשת חשבונית אוטומטית
def create_low_profile_payment(customer_email: str, customer_name: str) -> str:
    # פרטי החשבונית
    invoice_params = {
        "InvoiceHead.CustName": customer_name,       # שם הלקוח שיוצג בחשבונית
        "InvoiceHead.SendByEmail": "true",           # שליחת המסמך ללקוח
        "InvoiceHead.Email": customer_email,         # כתובת מייל הלקוח
        "InvoiceHead.Language": "he",                # חשבונית בעברית
        "InvoiceHead.CoinID": "1",                   # מטבע – 1 = ש"ח

        # פרטי המוצר בחשבונית (שורה 1)
        "InvoiceLines1.Description": "פונט אישי מכתב יד",   # תיאור הפריט
        "InvoiceLines1.Price": "24.90",                     # מחיר (ש"ח)
        "InvoiceLines1.Quantity": "1",                      # כמות
    }

    # פרטי העסקה והתשלום
    payment_params = {
        "terminalnumber": 172726 ,
        "username": 4cbscU43zRCYzL9YLSxV ,
        "LowProfileIndication": "1",  # הפעלת מנגנון Webhook
        "SumToBill": "24.90",         # סכום לתשלום (חייב להיות זהה לסה"כ בחשבונית)

        "SuccessRedirectUrl": SUCCESS_RETURN_URL,
        "ErrorRedirectUrl": ERROR_RETURN_URL,
        "CancelUrl": ERROR_RETURN_URL,

        "APILevel": "10",             # מומלץ לפי Cardcom
        "Operation": "1",             # חיוב רגיל

        "Language": "he",             # שפת הממשק
        "ProductName": "יצירת פונט אישי",  # יופיע במסך התשלום

        # חשוב! כדי להעביר עברית ב־POST – נשתמש ב־codepage
        "codepage": "65001"
    }

    # שילוב של פרטי התשלום + החשבונית
    full_payload = {**payment_params, **invoice_params}

    # המרת כל הערכים ל־URL encoding
    encoded_payload = urllib.parse.urlencode(full_payload)

    # שליחת הבקשה ל-Cardcom
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    response = requests.post(CARDCOM_LOW_PROFILE_URL, data=encoded_payload, headers=headers)

    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"שגיאה בקבלת תשלום: {response.status_code} - {response.text}")
