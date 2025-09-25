from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import openai

# ست کردن مستقیم API key
openai.api_key = "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"

app = FastAPI()

# Enable CORS for Flutter (and Postman testing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load contract data
with open("contract_text.json", "r", encoding="utf-8") as f:
    contract = json.load(f)

@app.post("/ask")
async def ask_question(request: Request):
    # Check if API key is available
    if not openai.api_key:
        return JSONResponse(
            status_code=500,
            content={"error": "OpenAI API key is missing."}
        )

    # Parse request body
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

    # Keep your original prompt
    prompt = f"""
    تو یک دستیار فارسی‌زبان هستی و باید به سوالات درباره این قرارداد پاسخ بدهی.

    هدف:
    - کمک کن کاربر بفهمه مفاد قرارداد چه معنی و اهمیتی دارند.
    - حتی اگر جواب مستقیم در قرارداد نبود، تحلیل و دلیل منطقی بیاور.

    سبک پاسخ:
    - کوتاه و محاوره‌ای باش.
    - ساده توضیح بده چرا بخش‌های مختلف قرارداد مهم هستند.
    - از عبارت‌های خشک یا رسمی بیش از حد استفاده نکن.

    اطلاعات قرارداد:
    {json.dumps(contract, ensure_ascii=False, indent=2)}

    سوال کاربر: {question}

    جواب را طوری بنویس که کاربر احساس کند یک مشاور دلسوز با او صحبت می‌کند.
    """

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        answer = response.choices[0].message.content.strip()
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
