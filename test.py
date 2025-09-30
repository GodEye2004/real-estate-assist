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

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # your ghp_xxx token
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not GITHUB_TOKEN:
    raise ValueError("❌ Missing GITHUB_TOKEN in .env")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ Missing Supabase config")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# FastAPI app
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load contract file
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
    body = await request.json()
    question = body.get("question", "").strip()

    if not question:
        return JSONResponse(status_code=400, content={"error": "Question field is required."})

    prompt = f"""
    تو یک دستیار فارسی‌زبان هستی و باید به سوالات درباره این قرارداد جواب کوتاه و محاوره‌ای بدی.

    اطلاعات قرارداد:
    {json.dumps(contract, ensure_ascii=False)}

    سوال کاربر: {question}
    """

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "openai/gpt-4o-mini",  # GitHub models proxy OpenAI models
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://models.github.ai/inference/chat/completions",
            headers=headers,
            json=payload,
        )

    if response.status_code != 200:
        return JSONResponse(status_code=response.status_code, content=response.json())

    data = response.json()
    answer = data["choices"][0]["message"]["content"]

    try:
        supabase.table("chat_logs").insert({
            "question": question,
            "answer": answer
        }).execute()
    except Exception as db_err:
        print("⚠️ Failed to save to Supabase:", db_err)

    return JSONResponse(content={"answer": answer})
