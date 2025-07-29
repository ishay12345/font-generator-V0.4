import requests 
import urllib.parse

# קונפיגורציה – מזהה ספק שלך וכו'
CARDCOM_TERMINAL_NUMBER = "172726"  # מספר טרמינל שלך (Cardcom Terminal Number)
CARDCOM_USER_NAME = "4cbscU43zRCYzL9YLSxV"  # שם משתמש API
CARDCOM_LOW_PROFILE_URL = "https://secure.cardcom.solutions/Interface/LowProfile.aspx"

# כתובת חזרה אחרי תשלום מוצלח / כישלון / Webhook
SUCCESS_RETURN_URL = "https://myfont.co.il/thankyou"               # ✅ דף תודה (ולא הורדה ישירה)
ERROR_RETURN_URL   = "https://myfont.co.il/payment?status=failed"
INDICATOR_URL      = "https://myfont.co.il/cardcom-indicator"     # ה־Webhook שלנו

# הפונקציה שמייצרת תשלום + מבקשת חשבונית
def create_low_profile_payment(customer_email: str, customer_name: str) -> str:
    # פרטי החשבונית
    invoice_params = {
        "InvoiceHead.CustName": customer_name,
        "InvoiceHead.SendByEmail": "true",
        "InvoiceHead.Email": customer_email,
        "InvoiceHead.Language": "he",
        "InvoiceHead.CoinID": "1",  # ש"ח

        "InvoiceLines1.Description": "פונט אישי מכתב יד",
        "InvoiceLines1.Price": "24.90",
        "InvoiceLines1.Quantity": "1"
    }

    # פרטי העסקה (חיוב)
    payment_params = {
        "terminalnumber": CARDCOM_TERMINAL_NUMBER,
        "username": CARDCOM_USER_NAME,
        "LowProfileIndication": "1",          # מבקש מהמערכת לשלוח את הנתונים ל-Webhook
        "IndicatorUrl": INDICATOR_URL,        # כאן תגיע התשובה מקרדקום לאחר התשלום

        "SumToBill": "24.90",                 # חשוב – חייב להיות זהה לסכום החשבונית

        "SuccessRedirectUrl": SUCCESS_RETURN_URL,  # ✅ אחרי תשלום – נשלח לדף תודה
        "ErrorRedirectUrl": ERROR_RETURN_URL,
        "CancelUrl": ERROR_RETURN_URL,

        "APILevel": "10",
        "Operation": "1",  # חיוב רגיל

        "Language": "he",
        "ProductName": "יצירת פונט אישי",

        "codepage": "65001"
    }

    # שילוב כל הפרמטרים
    full_payload = {**payment_params, **invoice_params}

    # המרה ל־URL encoding
    encoded_payload = urllib.parse.urlencode(full_payload)

    # שליחת הבקשה ל־Cardcom
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    response = requests.post(CARDCOM_LOW_PROFILE_URL, data=encoded_payload, headers=headers)

    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"שגיאה בקבלת תשלום: {response.status_code} - {response.text}")
