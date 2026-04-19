import os
import requests
from flask import Flask, request

app = Flask(__name__)
TEMP_DIR = "/tmp/"

def recognize_speech(file_path):
    import speech_recognition as sr
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(file_path) as source:
            audio = recognizer.record(source)
        return recognizer.recognize_google(audio, language="he-IL")
    except Exception as e:
        return f"שגיאת תמלול: {str(e)}"

def send_to_google_chat(full_url_g, key_g, token_g, text, phone, name, audio_url=None):
    """שליחת הודעה ל-Google Chat בפורמט הזירה הגרודנאית"""
    # בניית ה-URL המלא
    webhook_url = f"{full_url_g}?key={key_g}&token={token_g}"
    
    # בניית גוף ההודעה לפי הדרישות החדשות
    message_lines = [
        f"📢 *הודעה טלפונית חדשה מהזירה הגרודנאית*",
        f"📞 נשלח מטלפון: {phone}",
        f"💬 תוכן ההודעה: {text}",
        f"",
        f"🇮🇱 _נשלח באמצעות הפיתוח של אבי שיינין_"
    ]
    
    formatted_text = "\n".join(message_lines)
    payload = {"text": formatted_text}
    
    try:
        response = requests.post(webhook_url, json=payload)
        return response.status_code == 200
    except:
        return False

@app.route("/transcribe", methods=["GET"])
def transcribe():
    # פרמטרים מימות המשיח
    token = request.args.get('token', '')
    api_id = request.args.get('ApiCallId', '')
    phone = request.args.get('ApiPhone', 'לא ידוע')
    name = request.args.get('ApiEnterIDName', 'אורח')
    m_param = request.args.get('M', '7')
    
    # פרמטרים לגוגל צ'אט
    url_g = request.args.get('url-g', '')
    key_g = request.args.get('key_g', '')
    token_g = request.args.get('token_g', '')
    
    if not api_id: return "Missing ApiCallId", 400

    text_storage = os.path.join(TEMP_DIR, f"trans_{api_id}.txt")
    k_counter_file = os.path.join(TEMP_DIR, f"k_count_{api_id}.txt")

    def get_k_count():
        if not os.path.exists(k_counter_file): return 1
        with open(k_counter_file, "r") as f:
            try: return int(f.read().strip())
            except: return 1

    def set_k_count(val):
        with open(k_counter_file, "w") as f: f.write(str(val))

    current_k_num = get_k_count()
    current_ok_val = request.args.get(f'OK{current_k_num}', '')
    current_k_path = request.args.get(f'K{current_k_num}', '')

    # --- שלב 1: אישור ושליחה ---
    if current_ok_val == "1":
        if os.path.exists(text_storage):
            with open(text_storage, "r", encoding="utf-8") as f:
                final_text = f.read()
            
            success = send_to_google_chat(url_g, key_g, token_g, final_text, phone, name)
            
            # ניקוי קבצים
            for f in [text_storage, k_counter_file]:
                if os.path.exists(f): os.remove(f)
            
            return "id_list_message=m-1452."

    # --- שלב 2: תיקון ---
    if current_ok_val == "2":
        new_k_num = current_k_num + 1
        set_k_count(new_k_num)
        return f"read=m-1012=K{new_k_num},,record,{m_param},,no"

    # --- שלב 3: עיבוד הקלטה ---
    if current_k_path:
        down_url = f"https://www.call2all.co.il/ym/api/DownloadFile?token={token}&path=ivr2:{current_k_path}"
        res = requests.get(down_url)
        if res.status_code == 200:
            audio_tmp = os.path.join(TEMP_DIR, f"audio_{api_id}.wav")
            with open(audio_tmp, "wb") as f: f.write(res.content)
            text = recognize_speech(audio_tmp)
            if os.path.exists(audio_tmp): os.remove(audio_tmp)
            
            with open(text_storage, "w", encoding="utf-8") as f: f.write(text)
            return f"read=t-{text}.m-1078=OK{current_k_num},,1,1,,NO,,,,12,,,,,no"

    # --- שלב 0: התחלה ---
    if not current_k_path and not current_ok_val:
        set_k_count(1)
        return f"read=m-1012=K1,,record,{m_param},,no"

    return "id_list_message=f-Error_General."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
