import io

from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.params import Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import TypedDict
import os, json, httpx
from dotenv import load_dotenv
from requests.compat import chardet
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.future import select
import pdfplumber
import docx
from db_config import get_db
from models import TenatData


load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("❌ محیط GITHUB_TOKEN تنظیم نشده است!")

# ----------------------------
# FastAPI setup
# ----------------------------
app = FastAPI()



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




# ----------------------------
# حافظه موقت برای هر کاربر
# ----------------------------
user_sessions = {}  # user_id -> {"category": str, "data": dict}

# ----------------------------
# LLM
# ----------------------------
async def github_llm(prompt: str) -> str:
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "model": "openai/gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                "https://models.github.ai/inference/chat/completions",
                headers=headers,
                json=payload,
            )
        response.raise_for_status()

        # بررسی اینکه پاسخ خالی نباشه
        if not response.content.strip():
            return "⚠️ پاسخ از سرور دریافت نشد."

        # بررسی JSON معتبر
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    except httpx.HTTPStatusError as e:
        print(f"⚠️ GitHub API HTTP error: {e}")
        return f"⚠️ خطای HTTP: {e.response.status_code}"
    except json.JSONDecodeError:
        print("⚠️ پاسخ سرور JSON معتبر نیست")
        return "⚠️ فرمت پاسخ سرور نامعتبر است."
    except Exception as e:
        print(f"⚠️ GitHub API error: {e}")
        return "متأسفانه مشکلی در دریافت پاسخ پیش آمد."

# ----------------------------
# انتخاب کتگوری
# ----------------------------
@app.post("/select_category")
async def select_category(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    user_id = body.get("user_id")
    category = body.get("category")

    if not user_id or not category:
        return  JSONResponse(status_code=400, content={"error":"user_id and category are required"})

    existing = await db.execute(select(TenatData).where(TenatData.user_id == user_id))
    record = existing.scalars().first()

    if record:
        record.category = category
    else:
        record = TenatData(user_id=user_id, category=category, data={})
        db.add(record)

    await db.commit()
    return {"message": f"'{category}' active for you"}

# ----------------------------
# آپلود داده
# ----------------------------
# @app.post("/upload_json")
# async def upload_json(
#     user_id: str = Form(...),
#     category: str = Form(...),
#     file: UploadFile = File(...),
#     db: AsyncSession = Depends(get_db)
# ):
#     if not file.filename.endswith(".json"):
#         return {"error": "file must be json"}
#
#     content = await file.read()
#     try:
#         json_data = json.loads(content)
#     except Exception as e:
#         return {"error": "the json format not true"}
#
#     existing = await db.execute(select(TenatData).where(TenatData.user_id == user_id))
#     record = existing.scalars().first()
#
#     if record:
#         record.category = category
#         record.data = json_data
#     else:
#         record = TenatData(user_id=user_id, category=category, data=json_data)
#         db.add(record)
#
#     await db.commit()
#     return {"message": f"json file for '{category}' has been uploaded"}

@app.post("/upload_json")
async def upload_json(
    user_id: str = Form(...),
    category: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    content = await file.read()
    text_data = ""
    json_data = {}

    filename = file.filename.lower()

    try:
        if filename.endswith(".json"):
            # مستقیماً JSON خوانده شود
            json_data = json.loads(content.decode("utf-8", errors="ignore"))

        elif filename.endswith(".pdf"):
            # استخراج متن از PDF با پشتیبانی از فارسی
            pdf_file = io.BytesIO(content)
            with pdfplumber.open(pdf_file) as pdf:
                text_pages = []
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    text = text.replace("\u200c", "").strip()  # حذف نیم‌فاصله‌ی نامناسب
                    text_pages.append(text)
                text_data = "\n".join(text_pages)
            json_data = {"text": text_data}

        elif filename.endswith(".docx"):
            # استخراج متن از Word با حفظ ترتیب و خط جدید
            doc_file = io.BytesIO(content)
            document = docx.Document(doc_file)
            paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
            text_data = "\n".join(paragraphs)
            json_data = {"text": text_data}

        elif filename.endswith(".txt"):
            # تشخیص خودکار انکودینگ برای پشتیبانی از فارسی
            detected = chardet.detect(content)
            encoding = detected["encoding"] or "utf-8"
            text_data = content.decode(encoding, errors="ignore")
            json_data = {"text": text_data}

        else:
            return {"error": "Unsupported file type. Only JSON, PDF, DOCX, TXT allowed."}

        # ذخیره یا بروزرسانی در دیتابیس
        existing = await db.execute(select(TenatData).where(TenatData.user_id == user_id))
        record = existing.scalars().first()

        if record:
            record.category = category
            record.data = json_data
        else:
            record = TenatData(user_id=user_id, category=category, data=json_data)
            db.add(record)

        await db.commit()
        return {"message": f"File for '{category}' uploaded successfully and converted to JSON."}

    except Exception as e:
        return {"error": f"Failed to process file: {str(e)}"}


# ----------------------------
# پرسیدن سؤال
# ----------------------------
@app.post("/ask")
async def ask(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    user_id = body.get("user_id")
    question = body.get("question")

    if not user_id or not question:
        return JSONResponse(status_code=400, content={"error": "user_id and question is required."})

    result = await db.execute(select(TenatData).where(TenatData.user_id == user_id))
    record = result.scalars().first()

    if not record or not record.data:
        return JSONResponse(status_code=400, content={"error": "there is no content for this user."})

    prompt = f"""
    تو یک دستیار فارسی هستی.
    کاربر از کتگوری "{record.category}" استفاده می‌کند.
    از داده‌های زیر برای پاسخ به سؤال استفاده کن:
    {json.dumps(record.data, ensure_ascii=False, indent=2)}

    سوال کاربر: {question}

    پاسخ کوتاه، دقیق و طبیعی بده.
    """
    answer = await github_llm(prompt)
    return {"answer": answer}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("test:app", host="0.0.0.0", port=port)
