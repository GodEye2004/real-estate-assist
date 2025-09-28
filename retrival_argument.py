from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import openai
from supabase import create_client, Client

# --- CONFIG ---
openai.api_key = "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"

SUPABASE_URL = "https://wblcutafmsztpgrzcbyy.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndibGN1dGFmbXN6dHBncnpjYnl5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTkwNjY0NTAsImV4cCI6MjA3NDY0MjQ1MH0.jwiEUI2BFkh3f-M4B7K0DC5UMLJ_L_ZdWYlvh8CcgXU"

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

with open("contract_text.json", "r", encoding="utf-8") as f:
    contract = json.load(f)

@app.post("/ask")
async def ask_question(request: Request):
    if not openai.api_key:
        return JSONResponse(status_code=500, content={"error": "OpenAI API key is missing."})

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
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        answer = response.choices[0].message.content.strip()

        # --- SAVE TO SUPABASE ---
        try:
            supabase.table("chat_logs").insert({"question": question, "answer": answer}).execute()
        except Exception as db_err:
            print("⚠️ Failed to save to Supabase:", db_err)

        return JSONResponse(content={"answer": answer})

    except openai.AuthenticationError:
        return JSONResponse(status_code=401, content={"error": "OpenAI API key is invalid or expired."})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Internal server error: {str(e)}"})
