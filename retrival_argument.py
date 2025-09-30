from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import os
from supabase import create_client, Client
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

# --------------------------
# LOAD .env CONFIG
# --------------------------
load_dotenv()  # Load variables from .env file

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Check for missing environment variables
if not OPENAI_API_KEY:
    raise ValueError("❌ Missing OPENAI_API_KEY. Please set it in your .env or environment.")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ Missing SUPABASE_URL or SUPABASE_KEY. Please set them in your .env or environment.")

print("hello")
# Initialize clients
client = OpenAI(api_key=OPENAI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize FastAPI app
app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load contract data
try:
    with open("contract_text.json", "r", encoding="utf-8") as f:
        contract = json.load(f)
except FileNotFoundError:
    raise FileNotFoundError("❌ contract_text.json file not found. Please make sure it exists.")


# --------------------------
# POST /ask → Chatbot Q&A
# --------------------------
@app.post("/ask")
async def ask_question(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON payload."})

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

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        answer = response.choices[0].message.content.strip()

        # Save chat to Supabase
        try:
            supabase.table("chat_logs").insert({
                "question": question,
                "answer": answer
            }).execute()
        except Exception as db_err:
            print("⚠️ Failed to save to Supabase:", db_err)

        return JSONResponse(content={"answer": answer})

    except OpenAIError as e:
        return JSONResponse(status_code=401, content={"error": f"OpenAI authentication failed: {str(e)}"})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Internal server error: {str(e)}"})


# --------------------------
# GET /logs → View chat history
# --------------------------
@app.get("/logs")
async def get_logs():
    try:
        result = supabase.table("chat_logs").select("*").order("created_at", desc=True).execute()
        return {"data": result.data}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to fetch logs: {str(e)}"})
