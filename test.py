from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import httpx
from supabase import create_client, Client
from dotenv import load_dotenv

# --------------------------
# LOAD .env CONFIG
# --------------------------
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # your GitHub token
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not GITHUB_TOKEN:
    raise ValueError("❌ Missing GITHUB_TOKEN in .env")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ Missing Supabase config")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --------------------------
# FastAPI app
# --------------------------
app = FastAPI()

# Enable CORS for Flutter Web / any frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # در production بهتره فقط دامنه‌های مورد نظر بذاری
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------
# Load contract file
# --------------------------
try:
    with open("contract_text.json", "r", encoding="utf-8") as f:
        contract = json.load(f)
except FileNotFoundError:
    raise FileNotFoundError("❌ contract_text.json not found.")

# --------------------------
# POST /ask → GitHub Models Q&A
# --------------------------
@app.post("/ask")
async def ask_question(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body."})

    question = body.get("question", "").strip()
    if not question:
        return JSONResponse(status_code=400, content={"error": "Question field is required."})

    prompt = f"""
    تو یک دستیار فارسی‌زبان هستی و باید به سوالات درباره این قرارداد جواب کوتاه و محاوره‌ای بدی.

    هدف:
    - کمک کن کاربر معنی و اهمیت مفاد قرارداد را بفهمد.
    - حتی اگر جواب مستقیم نبود، با دلیل منطقی تحلیل کن.

    سبک پاسخ:
    - کوتاه و ساده باش.
    - مثل یک مشاور دلسوز حرف بزن، خشک و رسمی نباش.

    اطلاعات قرارداد:
    {json.dumps(contract, ensure_ascii=False)}

    سوال کاربر: {question}

    جواب را کوتاه و روان بده.
    """

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "openai/gpt-4o-mini",  # GitHub models proxy OpenAI
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                "https://models.github.ai/inference/chat/completions",
                headers=headers,
                json=payload,
            )

        if response.status_code != 200:
            return JSONResponse(status_code=response.status_code, content={
                "error": f"GitHub model error: {response.text}"
            })

        data = response.json()
        answer = data["choices"][0]["message"]["content"]

    except httpx.RequestError as e:
        return JSONResponse(status_code=500, content={"error": f"Server request failed: {str(e)}"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Unexpected server error: {str(e)}"})

    # Save chat log to Supabase
    try:
        supabase.table("chat_logs").insert({
            "question": question,
            "answer": answer
        }).execute()
    except Exception as db_err:
        print("⚠️ Failed to save to Supabase:", db_err)

    return JSONResponse(content={"answer": answer})
