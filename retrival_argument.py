# retrival_argument.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import openai
import os
from supabase import create_client, Client

# --------------------------
# CONFIG FROM ENVIRONMENT
# --------------------------
openai.api_key = os.getenv("OPENAI_API_KEY")  # Set this in Render Environment Variables
SUPABASE_URL = os.getenv("SUPABASE_URL")     # Set this in Render Environment Variables
SUPABASE_KEY = os.getenv("SUPABASE_KEY")     # Set this in Render Environment Variables

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
with open("contract_text.json", "r", encoding="utf-8") as f:
    contract = json.load(f)

# --------------------------
# POST /ask → Chatbot Q&A
# --------------------------
@app.post("/ask")
async def ask_question(request: Request):
    if not openai.api_key:
        return JSONResponse(
            status_code=500,
            content={"error": "OpenAI API key is missing."}
        )

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid JSON payload."}
        )

    question = body.get("question", "").strip()
    if not question:
        return JSONResponse(
            status_code=400,
            content={"error": "Question field is required."}
        )

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
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        answer = response.choices[0].message.content.strip()

        # --- SAVE TO SUPABASE ---
        try:
            supabase.table("chat_logs").insert({
                "question": question,
                "answer": answer
            }).execute()
        except Exception as db_err:
            print("⚠️ Failed to save to Supabase:", db_err)

        return JSONResponse(content={"answer": answer})

    except openai.AuthenticationError:
        return JSONResponse(
            status_code=401,
            content={"error": "OpenAI API key is invalid or expired."}
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Internal server error: {str(e)}"}
        )


# --------------------------
# GET /logs → View chat history
# --------------------------
@app.get("/logs")
async def get_logs():
    try:
        result = supabase.table("chat_logs").select("*").order("created_at", desc=True).execute()
        return {"data": result.data}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to fetch logs: {str(e)}"}
        )
