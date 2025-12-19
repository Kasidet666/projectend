import os
import json
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from google import genai
from google.genai.errors import APIError
import pdfplumber # <-- NEW: สำหรับอ่านไฟล์ PDF
import io          # <-- NEW: สำหรับจัดการ stream ไฟล์ในหน่วยความจำ

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
    # หากตั้งค่าไม่สำเร็จ จะยกเลิกการโหลด Server
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
        return "Error: Frontend file (index.html) not found! Ensure it is in the same directory.", 500

# --- Endpoint สำหรับสรุปบทความ (API) ---
@app.route('/summarize', methods=['POST'])
def summarize_article():
    # 1. ตรวจสอบสถานะ Client 
    if not client:
        return jsonify({
            'error': 'Backend Initialization Failed. Check GEMINI_API_KEY setting.'
        }), 500
    
    article_text = ""
    
    try:
        # --- A. จัดการข้อมูลที่มาจาก FormData (รองรับทั้งไฟล์และข้อความ) ---
        
        # 1.1 ตรวจสอบการอัปโหลดไฟล์ PDF
        if 'pdf_file' in request.files:
            pdf_file = request.files['pdf_file']
            
            if pdf_file.filename != '' and pdf_file.filename.lower().endswith('.pdf'):
                # อ่านไฟล์ PDF ในหน่วยความจำ (bytes)
                file_stream = io.BytesIO(pdf_file.read())
                
                # ใช้ pdfplumber ดึงข้อความทั้งหมด
                with pdfplumber.open(file_stream) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            article_text += page_text + "\n"
                
                if not article_text.strip():
                     return jsonify({"error": "ไม่พบข้อความในไฟล์ PDF หรือไฟล์ว่างเปล่า"}), 400
            
            else:
                return jsonify({"error": "ไฟล์ที่อัปโหลดไม่ใช่ไฟล์ PDF ที่ถูกต้อง"}), 400

        # 1.2 หากไม่มีไฟล์ PDF ให้ดึงข้อความจาก form-data ธรรมดาแทน
        elif 'article_text' in request.form:
             article_text = request.form['article_text']
        
        # 1.3 ตรวจสอบว่ามีข้อมูลสำหรับสรุปหรือไม่
        if not article_text.strip():
            return jsonify({'error': 'No article text or valid PDF provided. Please input the content.'}), 400

        # 2. สร้าง Prompt และ Schema สำหรับ Gemini
        
        # Prompt สำหรับการสร้างเนื้อหา
        prompt_content = f"""
            Summarize the article, extract key concepts/keywords, and generate relevant FAQs. 
            The response must be in the same language as the input text.
            --- TEXT TO SUMMARIZE ---
            {article_text}
        """

        # JSON Schema: ตรงกับที่ Frontend คาดหวัง
        response_schema = {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "สรุปเนื้อหาบทความ"},
                "keywords": {"type": "array", "items": {"type": "string", "description": "คำสำคัญ"}},
                "faqs": {
                    "type": "array",
                    "description": "คำถามที่พบบ่อย 3 ข้อ",
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

        # 3. เรียกใช้ Gemini API
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_content,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                system_instruction=(
                    "You are a professional article summarizer. Your response must STRICTLY "
                    "be a single JSON object using the provided JSON schema. Do not include "
                    "any text outside the JSON block."
                ),
                response_schema=response_schema
            ),
        )

        # 4. ส่งผลลัพธ์กลับไปยัง Frontend
        # response.text คือ JSON string ที่ได้จาก Gemini
        return jsonify({'result': response.text}), 200

    except APIError as e:
        # จัดการข้อผิดพลาดที่เกี่ยวกับ Gemini API โดยเฉพาะ (เช่น Key ไม่ถูกต้อง)
        print(f"--- GEMINI API ERROR ---: {e}")
        return jsonify({
            'error': 'API Key Not Valid or API Request Failed. Check Terminal Log.'
        }), 500
        
    except Exception as e:
        # จัดการข้อผิดพลาดทั่วไปอื่น ๆ (รวมถึงปัญหาการอ่านไฟล์ PDF)
        print(f"--- GENERAL SERVER ERROR ---: {e}") 
        return jsonify({'error': f'Internal Server Error: {str(e)}'}), 500

if __name__ == '__main__':
    # รันบน host '0.0.0.0' เพื่อให้เข้าถึงได้จาก LAN (ต้องเปิด Firewall ด้วย)
    # ใช้งานร่วมกับ index.html ที่เรียกใช้ http://172.16.30.200:5000/summarize ได้
    app.run(debug=True, host='0.0.0.0', port=5000)