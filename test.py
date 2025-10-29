from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.params import Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import TypedDict
import os, json, httpx
from dotenv import load_dotenv
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
    # استخراج متن بر اساس نوع فایل
    content = await file.read()
    text_data = ""

    if file.filename.endswith(".json"):
        try:
            json_data = json.loads(content)
        except Exception:
            return {"error": "JSON format is not valid"}
    elif file.filename.endswith(".pdf"):
        import io
        pdf_file = io.BytesIO(content)
        with pdfplumber.open(pdf_file) as pdf:
            text_data = "\n".join([page.extract_text() or "" for page in pdf.pages])
        json_data = {"text": text_data}
    elif file.filename.endswith(".docx"):
        import io
        doc_file = io.BytesIO(content)
        doc = docx.Document(doc_file)
        text_data = "\n".join([para.text for para in doc.paragraphs])
        json_data = {"text": text_data}
    elif file.filename.endswith(".txt"):
        text_data = content.decode("utf-8")
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
    return {"message": f"File for '{category}' has been uploaded and converted to JSON."}



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
