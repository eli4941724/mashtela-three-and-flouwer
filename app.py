from flask import Flask, request, redirect, render_template_string, render_template, url_for
import requests
import os
import pandas as pd

app = Flask(__name__)

# סודות מהסביבה
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.environ.get("TWILIO_FROM")
TWILIO_TO = os.environ.get("TWILIO_TO")
IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY")

UPLOAD_URL = 'https://api.imgbb.com/1/upload'

def upload_image_to_imgbb(image_file):
    try:
        response = requests.post(UPLOAD_URL, params={"key": IMGBB_API_KEY},
                                 files={"image": image_file.read()})
        data = response.json()
        return data['data']['url'] if 'data' in data else None
    except Exception as e:
        print("Image upload failed:", e)
        return None

@app.route('/')
def home():
    return render_template('form.html')

@app.route('/catalog')
def show_plants():
    plants = pd.read_csv('plants.csv')
    for plant in plants.to_dict(orient='records'):
        plant['image'] = url_for('static', filename=f'images/{plant["image"]}')
    return render_template('plants.html', plants=plants.to_dict(orient='records'))

@app.route('/send', methods=['POST'])
def send():
    full_name = request.form.get('fullName', '')
    phone = request.form.get('phone', '')
    address = request.form.get('address', '')
    cart_data = request.form.get('cartData', '{}')
    image = request.files.get('image')

    image_url = None
    if image and image.filename:
        image_url = upload_image_to_imgbb(image)

    message = f"✉️ הזמנה חדשה מהמשתלה!\n\n"
    message += f"👤 שם: {full_name}\n"
    message += f"📞 טלפון: {phone}\n"
    message += f"📍 כתובת: {address}\n\n"
    message += f"📦 פריטים בעגלה:\n"

    try:
        items = eval(cart_data)
        for name, item in items.items():
            message += f"- {name} x{item['quantity']}\n"
    except Exception as e:
        message += "(שגיאה בקריאת העגלה)\n"
        print("Cart parse error:", e)

    if image_url:
        message += f"\n📷 תמונה מצורפת: {image_url}"

    send_whatsapp_message(message)

    return render_template_string("<h2>ההזמנה נשלחה (או נכשלה) – בדקי את הלוגים</h2><a href='/'>חזרה</a>")

def send_whatsapp_message(body):
    url = f'https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json'
    auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    data = {
        'From': TWILIO_FROM,
        'To': TWILIO_TO,
        'Body': body
    }

    try:
        print("📤 שולחת הודעה ל-Twilio...")
        response = requests.post(url, data=data, auth=auth)
        print("Twilio status:", response.status_code)
        print("Response:", response.text)

        if response.status_code == 201:
            print("✅ ההודעה נשלחה בהצלחה!")
        else:
            raise Exception(f"❌ שגיאה בשליחה ל-Twilio: {response.status_code}, {response.text}")
    except Exception as e:
        print("⚠️ חריגה בזמן שליחת WhatsApp:", e)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
