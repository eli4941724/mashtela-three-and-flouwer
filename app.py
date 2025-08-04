from flask import Flask, request, render_template, jsonify
import pandas as pd
import requests
import os

app = Flask(__name__)

# הגדרת משתנים מהסביבה
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.environ.get("TWILIO_FROM")
TWILIO_TO = os.environ.get("TWILIO_TO")
IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY")
UPLOAD_URL = 'https://api.imgbb.com/1/upload'

# דף הבית
@app.route('/')
def form():
    return render_template('form.html')

# החזרת רשימת הצמחים
@app.route('/plants')
def get_plants():
    df = pd.read_csv('plants.csv')
    return jsonify(df.to_dict(orient='records'))

# העלאת תמונה ל־ImgBB
def upload_image_to_imgbb(image_file):
    try:
        response = requests.post(
            UPLOAD_URL,
            params={"key": IMGBB_API_KEY},
            files={"image": image_file.read()}
        )
        data = response.json()
        return data['data']['url'] if 'data' in data else None
    except Exception as e:
        print("Image upload failed:", e)
        return None

# שליחת ההודעה
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

    # שליחת הודעה ל־Twilio
    url = f'https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json'
    auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    data = {
        'From': TWILIO_FROM,
        'To': TWILIO_TO,
        'Body': message
    }

    try:
        response = requests.post(url, data=data, auth=auth)
        print("Twilio status:", response.status_code)
        print("Response:", response.text)
        if response.status_code == 201:
            return 'ההודעה נשלחה בהצלחה!'
        else:
            return f"שגיאה בשליחה: {response.status_code}"
    except Exception as e:
        print("שגיאה בשליחה ל־Twilio:", e)
        return 'שגיאה בשליחה ל־Twilio'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

