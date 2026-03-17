import os
from dotenv import load_dotenv
load_dotenv()  # ده هيقرأ ملف .env لو موجود محليًا

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from typing import List
import shutil

app = FastAPI(title="🧬 Dr. GeneX API")

# CORS عشان Flutter أو أي frontend يقدر يتصل
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # غيريه لاحقًا للـ domains الحقيقية لو عايزة أمان أكتر
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# قراءة الـ API Key من الـ environment variables (مهم جدًا في Railway)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is missing! Set it in Railway Variables.")

# تهيئة Gemini مرة واحدة
genai.configure(api_key=GEMINI_API_KEY)

# استخدام GenerativeModel (الطريقة الصحيحة والموصى بها)
model = genai.GenerativeModel("gemini-2.5-flash")

# الذاكرة المؤقتة (ستستمر طالما السيرفر شغال بدون إعادة تشغيل)
chat_history = []

# مجلد حفظ الملفات المرفوعة
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.get("/")
async def root():
    return {"message": "🧬 Dr. GeneX API is running - session is persistent"}


@app.post("/chat")
async def chat(user_input: str):
    global chat_history
    
    # حفظ رسالة المستخدم
    chat_history.append({"role": "user", "content": user_input})
    
    # آخر 8 رسائل فقط عشان الـ context ما يبقاش كبير جدًا
    recent_history = chat_history[-8:]
    history_text = "\n".join(
        f"{msg['role']}: {msg['content']}" for msg in recent_history
    )
    
    prompt = f"""أنت دكتور جين إكس، كوتش جيني ودود جدًا.
رد بالعامية المصرية لو اليوزر كتب عامية، فصحى لو فصحى، إنجليزي لو إنجليزي.
استخدم إيموجي طبيعي.
ادمج نصايح أكل ورياضة وصحة نفسية.
ممنوع تشخيص طبي أبدًا، دايمًا قول استشر طبيب.
الذاكرة السابقة:
{history_text}
السؤال الجديد: {user_input}"""

    try:
        response = model.generate_content(
            contents=[{"role": "user", "parts": [{"text": prompt}]}]
        )
        
        # التأكد من وجود رد صالح
        if not response.candidates or not response.candidates[0].content.parts:
            return {"error": "لم يتم الحصول على رد صالح من النموذج"}
        
        reply = response.candidates[0].content.parts[0].text.strip()
        
        # حفظ رد النموذج في الـ history
        chat_history.append({"role": "model", "content": reply})
        
        return {
            "reply": reply,
            "history_length": len(chat_history)
        }
    
    except Exception as e:
        error_msg = str(e)
        # لو الخطأ بسبب النموذج، ممكن نرجع رسالة واضحة
        if "not found" in error_msg.lower() or "not supported" in error_msg.lower():
            return {"error": "النموذج غير متاح حاليًا، جرب نموذج آخر أو تحقق من الـ API Key"}
        return {"error": f"خطأ في الاتصال بـ Gemini: {error_msg}"}


@app.post("/upload")
async def upload_file(files: List[UploadFile] = File(...)):
    saved = []
    for file in files:
        path = os.path.join(UPLOAD_DIR, file.filename)
        with open(path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        saved.append(file.filename)
    return {"uploaded": saved}


@app.get("/history")
async def get_history():
    return {"history": chat_history}


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Dr. GeneX API ...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)