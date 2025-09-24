from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import json
import openai

# ست کردن مستقیم API key
openai.api_key = "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"

app = FastAPI()

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

    body = await request.json()
    question = body.get("question", "").strip()

    if not question:
        return JSONResponse(
            status_code=400,
            content={"error": "Question field is required."}
        )

    prompt = f"""
تو یک دستیار هوشمند فارسی‌زبان هستی که وظیفه‌ات پاسخ‌گویی و تحلیل سوالات مربوط به قرارداد زیر است.

نقش طرفین در این قرارداد:
- طرف اول: شرکت هومنگر
- طرف دوم: مشتری

وظیفه تو:
- پاسخ‌گویی دقیق و رسمی به سوالات
- اگر اطلاعات مستقیم وجود ندارد، از زمینه قرارداد تحلیل منطقی ارائه بده
- پاسخ باید کوتاه، مستدل و با نگارش رسمی فارسی باشد
- از هیچ منبع خارجی استفاده نکن، فقط بر اساس اطلاعات قرارداد تحلیل کن
- اگر هیچ اطلاعات یا زمینه‌ای وجود ندارد، محترمانه اعلام کن

اطلاعات قرارداد:
{json.dumps(contract, ensure_ascii=False, indent=2)}

سوال: {question}
پاسخ را فقط بر اساس اطلاعات بالا، به زبان فارسی و با نگارش محاوره ایی و صمیمی بنویس.
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