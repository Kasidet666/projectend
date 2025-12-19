# app.py - AI Summary Backend Server (Final Version)
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from google import genai
from google.genai.errors import APIError
import os
import json

# --- การตั้งค่า Flask Server ---
app = Flask(__name__)
# อนุญาต CORS สำหรับการใช้งานระหว่าง Local (Dev/LAN)
CORS(app) 

# --- การตั้งค่า Gemini API Client ---
try:
    # ดึง API Key จาก Environment Variable
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Environment Variable 'GEMINI_API_KEY' is not set.")
    
    client = genai.Client(api_key=api_key)
    print("--- Gemini API Client Initialized Successfully ---")
    
except Exception as e:
    # หากตั้งค่าไม่สำเร็จ จะยกเลิกการโหลด Server (คล้ายข้อความเริ่มต้น)
    print(f"FATAL ERROR: Failed to initialize Gemini Client: {e}")
    client = None # ตั้งให้ client เป็น None เพื่อป้องกันการเรียกใช้ที่ผิดพลาด

# --- Endpoint สำหรับแสดงหน้าเว็บ (Frontend) ---
@app.route('/', methods=['GET'])
def serve_frontend():
    """ให้บริการไฟล์ index.html เมื่อผู้ใช้เข้าสู่ URL หลัก"""
    try:
        # อ่านเนื้อหาของไฟล์ index.html
        with open('index.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        return render_template_string(html_content)
    except FileNotFoundError:
        return "Error: Frontend file (index.html) not found!", 500

# --- Endpoint สำหรับสรุปบทความ (API) ---
@app.route('/summarize', methods=['POST'])
def summarize_article():
    # 1. ตรวจสอบสถานะ Client 
    if not client:
        return jsonify({
            'error': 'Backend Initialization Failed. Check GEMINI_API_KEY setting.'
        }), 500
        
    try:
        # 2. ดึงข้อมูลจาก Frontend
        data = request.get_json()
        # ใช้ Key 'article_text' ตามที่ Frontend ส่งมา
        article_text = data.get('article_text', '').strip() 
        
        if not article_text:
            return jsonify({'error': 'No article text provided. Please input the content.'}), 400

        # 3. สร้าง Prompt สำหรับ Gemini
        # ใช้ System Instruction เพื่อบังคับโครงสร้างและภาษา
        prompt = (
            "Summarize the article, extract 3 main keywords, and generate 2 frequently "
            "asked questions (FAQs) about the content. Response must be in Thai."
        )
        
        # 4. เรียกใช้ Gemini API
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, article_text],
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                system_instruction=(
                    "You are a professional article summarizer. Your response must STRICTLY "
                    "be a single JSON object using the following structure. Do not include "
                    "any text outside the JSON block."
                ),
                response_schema={
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string", "description": "สรุปเนื้อหาบทความ"},
                        "keywords": {"type": "array", "items": {"type": "string"}},
                        "faqs": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "question": {"type": "string"},
                                    "answer": {"type": "string"}
                                },
                                "required": ["question", "answer"]
                            }
                        }
                    },
                    "required": ["summary", "keywords", "faqs"]
                }
            ),
        )

        # 5. ส่งผลลัพธ์กลับไปยัง Frontend
        # response.text คือ JSON string ที่ได้จาก Gemini
        return jsonify({'result': response.text}), 200

    except APIError as e:
        # จัดการข้อผิดพลาดที่เกี่ยวกับ Gemini API โดยเฉพาะ (เช่น Key ไม่ถูกต้อง)
        print(f"--- GEMINI API ERROR ---: {e}")
        return jsonify({
            'error': 'API Key Not Valid or API Request Failed. Check Terminal Log.'
        }), 500
        
    except Exception as e:
        # จัดการข้อผิดพลาดทั่วไปอื่น ๆ
        print(f"--- GENERAL SERVER ERROR ---: {e}") 
        return jsonify({'error': f'Internal Server Error: {str(e)}'}), 500

if __name__ == '__main__':
    # รันบน host '0.0.0.0' เพื่อให้เข้าถึงได้จาก LAN (ต้องเปิด Firewall ด้วย)
    app.run(debug=True, host='0.0.0.0', port=5000)