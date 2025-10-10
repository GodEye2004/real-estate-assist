from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os, json, httpx, statistics
from supabase import create_client, Client
from dotenv import load_dotenv

# --------------------------
# LOAD .env CONFIG
# --------------------------
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not GITHUB_TOKEN:
    raise ValueError("❌ Missing GITHUB_TOKEN in .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------
# Load Real Estate Data
# --------------------------
try:
    with open("datasposts.json", "r", encoding="utf-8") as f:
        real_estate_data = json.load(f)
except FileNotFoundError:
    raise FileNotFoundError("❌ datasposts.json not found.")


# --------------------------
# Helper: Extract summary insights
# --------------------------
def generate_market_summary(listings):
    """تولید تحلیل خلاصه از داده‌ها"""
    try:
        prices = []
        rooms_list = []
        cities = {}

        for item in listings:
            data = item.get("data", {})
            city = item.get("city", "")
            rooms = data.get("rooms")
            price = data.get("new_price")
            size = data.get("size")

            # فقط قیمت‌های عددی را بگیر
            if isinstance(price, (int, float)):
                prices.append(price)
            elif isinstance(price, str) and price.replace('.', '').isdigit():
                prices.append(float(price))

            if rooms:
                rooms_list.append(int(rooms))

            if city:
                cities[city] = cities.get(city, 0) + 1

        if not prices:
            return "فعلاً داده‌ای برای تحلیل قیمت موجود نیست."

        avg_price = int(statistics.mean(prices))
        min_price = int(min(prices))
        max_price = int(max(prices))
        avg_rooms = round(statistics.mean(rooms_list), 1) if rooms_list else "نامشخص"

        popular_city = max(cities, key=cities.get) if cities else "نامشخص"

        summary = (
            f"میانگین قیمت خونه‌های موجود حدود {avg_price:,} تومنه. "
            f"بازه‌ی قیمتی بین {min_price:,} تا {max_price:,} تومنه. "
            f"میانگین تعداد اتاق‌ها حدود {avg_rooms} خوابه. "
            f"محبوب‌ترین منطقه فعلی بین فایل‌ها، {popular_city} هست."
        )

        return summary
    except Exception as e:
        return f"خطا در تحلیل داده‌ها: {e}"


def analyze_listings(listings):
    """تحلیل خلاصه از لیست ملک‌ها"""
    if not listings:
        return "ملکی برای تحلیل پیدا نشد."

    prices = []
    rooms_list = []
    cities = []

    for item in listings:
        try:
            price = item.get("price")
            if isinstance(price, str):
                # تبدیل قیمت رشته‌ای به عددی
                price = int(price.replace(",", "").replace("تومان", "").strip())
            if price:
                prices.append(price)
        except:
            pass

        rooms = item.get("rooms")
        if rooms:
            try:
                rooms_list.append(int(rooms))
            except:
                pass

        city = item.get("city")
        if city:
            cities.append(city)

    avg_price = sum(prices) / len(prices) if prices else None
    avg_rooms = sum(rooms_list) / len(rooms_list) if rooms_list else None

    common_cities = sorted(set(cities), key=cities.count, reverse=True)[:3]
    common_cities_str = "، ".join(common_cities)

    summary = "الان در بازار "
    if common_cities:
        summary += f"{common_cities_str} "
    summary += "خانه‌هایی "
    if avg_rooms:
        summary += f"با حدود {round(avg_rooms)} اتاق "
    if avg_price:
        summary += f"به‌طور میانگین حدود {int(avg_price/1_000_000_000)} میلیارد تومان قیمت دارن."
    else:
        summary += "در بازه‌های قیمتی مختلف وجود دارن."

    return summary


# --------------------------
# Helper: Find relevant listings
# --------------------------
def find_relevant_listings(question: str, limit: int = 15):
    q = question.lower()
    results = []

    for item in real_estate_data:
        title = item.get("data", {}).get("title", "")
        desc = item.get("data", {}).get("description", "")
        city = item.get("city", "")
        category = item.get("category", "")
        text = f"{title} {desc} {city} {category}".lower()

        if any(keyword in text for keyword in q.split()):
            results.append(item)
            if len(results) >= limit:
                break
    return results


# --------------------------
# POST /ask
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

    # 🔍 پیدا کردن ملک‌های مرتبط
    relevant = find_relevant_listings(question)

    if not relevant:
        return JSONResponse(content={"answer": "فعلاً ملکی مرتبط با این توضیحات پیدا نکردم."})

    # 📊 ساخت خلاصه تحلیلی از داده‌ها
    market_summary = analyze_listings(relevant)

    # ✂️ خلاصه‌سازی داده‌های ارسالی برای جلوگیری از خطای 413
    short_relevant = []
    for item in relevant[:5]:  # فقط 5 ملک
        short_relevant.append({
            "title": item.get("title"),
            "price": item.get("price"),
            "rooms": item.get("rooms"),
            "city": item.get("city"),
            "size": item.get("size"),
        })

    # 🧠 ساخت پرامپت برای مدل
    prompt = f"""
    تو یک مشاور املاک فارسی‌زبان در شهر گرگان هستی و باید به سوالات کاربران درباره خرید، فروش و سرمایه‌گذاری ملک پاسخ بدی.

    📘 دانش محلی (مناطق مهم گرگان):
    - مناطق بالاشهر گرگان شامل: ناهارخوران، صیاد، النگ‌دره، و گلشهر هستند.
    - مناطق متوسط: عدالت، شهید رجایی، کمربندی.
    - مناطق اقتصادی‌تر: خزانه، سروش، افسران.
    - ناهارخوران منطقه‌ای خوش‌آب‌وهوا و لوکس است، نزدیک جنگل.
    - گلشهر مدرن‌تر و نزدیک مراکز خرید است.
    - النگ‌دره به دلیل طبیعت و نزدیکی به جنگل بین مردم محبوب است.

    📈 خلاصه بازار:
    {market_summary}

    📄 نمونه ملک‌ها:
    {json.dumps(short_relevant, ensure_ascii=False)}

    🗣️ سوال کاربر: {question}

    جواب را طبیعی، محاوره‌ای و خلاصه بنویس، طوری که شبیه یک مشاور باتجربه املاک باشی.
    """

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "openai/gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
        "max_tokens": 400,  # محدود کردن پاسخ برای اطمینان
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
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

    # 💾 ذخیره در Supabase (در صورت وجود)
    try:
        supabase.table("chat_logs").insert({
            "question": question,
            "answer": answer
        }).execute()
    except Exception as db_err:
        print("⚠️ Failed to save to Supabase:", db_err)

    # ✅ پاسخ نهایی به کلاینت
    return JSONResponse(content={"answer": answer})
