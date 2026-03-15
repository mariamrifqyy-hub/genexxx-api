import os
from dotenv import load_dotenv
load_dotenv()  # ده هيقرأ ملف .env تلقائيًا
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from typing import List
import shutil

app = FastAPI(title="🧬 Dr. GeneX API")

# CORS عشان تفتحي من الفرونت لو عندك
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# قراءة الـ API Key من المتغيرات البيئية فقط
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is missing! Set it in environment variables.")

# تهيئة الـ client مرة واحدة
client = genai.Client(api_key=GEMINI_API_KEY)

# الذاكرة (ستستمر طالما السيرفر شغال)
chat_history = []

# مجلد الرفع (اختياري)
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.get("/")
async def root():
    return {"message": "🧬 Dr. GeneX API is running - session is persistent"}


@app.post("/chat")
async def chat(user_input: str):
    global chat_history

    # حفظ الرسالة الجديدة
    chat_history.append({"role": "user", "content": user_input})

    # آخر 8 رسائل فقط (context window صغير)
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
        response = client.models.generate_content(
            model="models/gemini-1.5-flash-002",   # ← أحدث نسخة مستقرة في 2026
            contents=[{"role": "user", "parts": [{"text": prompt}]}]
        )

        reply = response.candidates[0].content.parts[0].text.strip()
        chat_history.append({"role": "model", "content": reply})

        return {
            "reply": reply,
            "history_length": len(chat_history)
        }

    except Exception as e:
        return {"error": str(e)}


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