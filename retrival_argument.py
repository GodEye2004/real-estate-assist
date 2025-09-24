from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import json
import openai
import os

# بارگذاری کلید API از فایل .env (اختیاری و امن‌تر)
openai.api_key = "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"

app = FastAPI()

# بارگذاری داده‌های قرارداد
with open("contract_text.json", "r", encoding="utf-8") as f:
    contract = json.load(f)

@app.post("/ask")
async def ask_question(request: Request):
    body = await request.json()
    question = body.get("question", "")

    # ساخت پرامپت دقیق و فارسی
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
    پاسخ را فقط بر اساس اطلاعات بالا، به زبان فارسی و با نگارش رسمی بنویس.
    """

    # فراخوانی مدل GPT-4o-mini
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    # استخراج پاسخ
    answer = response.choices[0].message.content.strip()

    return JSONResponse(content={"answer": answer})