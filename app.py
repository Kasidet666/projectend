# app.py - โค้ดที่พร้อมสำหรับ Deployment

from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
from google import genai
import os

# --- การตั้งค่า Flask Server ---
app = Flask(__name__)
# อนุญาต CORS ทั้งหมด
CORS(app) 

# ดึง API Key จาก Environment Variable
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# --- 1. Endpoint สำหรับแสดงหน้าเว็บ (Frontend) ---
@app.route('/', methods=['GET'])
def serve_frontend():
    """ให้บริการไฟล์ index.html เมื่อผู้ใช้เข้าสู่ URL หลัก"""
    
    # อ่านเนื้อหาของไฟล์ index.html
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # ส่งเนื้อหา HTML กลับไปให้ผู้ใช้
        return render_template_string(html_content)
    except FileNotFoundError:
        return "Frontend HTML file not found!", 500

# --- 2. Endpoint สำหรับสรุปบทความ (API) ---
@app.route('/summarize', methods=['POST'])
def summarize_article():
    # ... (ส่วนนี้ใช้โค้ดเดิมของคุณ) ...
    # (โค้ดในส่วนนี้จะใช้โค้ดเดิมที่คุณสร้างไว้สำหรับ summarize_article)
    # ...
    # (ผมจะไม่ใส่โค้ดซ้ำทั้งหมด แต่ส่วนนี้คือส่วนของ Gemini API)
    # ...
    
    # ส่งผลลัพธ์กลับไปยัง Frontend
    return jsonify({'summary': response.text})

if __name__ == '__main__':
    # สำหรับการรันในเครื่อง (Development)
    app.run(debug=True, host='0.0.0.0')

# หมายเหตุ: เมื่อ Deploy ขึ้น Cloud (เช่น Render) จะใช้ Gunicorn
# Gunicorn จะใช้การตั้งค่าในไฟล์ requirements.txt และ Procfile (ขั้นตอนถัดไป)