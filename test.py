from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os, json
from supabase import create_client, Client
from dotenv import load_dotenv
from langgraph.graph import StateGraph
from typing import TypedDict
import httpx

# ----------------------------
# بارگذاری محیط
# ----------------------------
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not all([GITHUB_TOKEN, SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("❌ Missing environment variables!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ----------------------------
# خواندن داده‌های دانش
# ----------------------------
knowledge_dir = "knowledge"
knowledge_data = {}
if not os.path.exists(knowledge_dir):
    os.makedirs(knowledge_dir)

for fname in os.listdir(knowledge_dir):
    if fname.endswith(".json"):
        topic = fname.replace(".json", "")
        with open(os.path.join(knowledge_dir, fname), "r", encoding="utf-8") as f:
            knowledge_data[topic] = json.load(f)

print("✅ Loaded topics:", list(knowledge_data.keys()))

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
# تعریف State
# ----------------------------
class QAState(TypedDict, total=False):
    question: str
    answer: str


# ----------------------------
# تابع کمکی برای فراخوانی API گیتهاب
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
        response.raise_for_status()  # Raise error if not 200
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"⚠️ GitHub API error: {e}")
        return "متأسفانه مشکلی در دریافت پاسخ پیش آمد."


# ----------------------------
# Node برای پاسخ‌دهی
# ----------------------------
async def responder(state: QAState) -> dict:
    question = state["question"]
    combined_info = json.dumps(knowledge_data, ensure_ascii=False)  # تمام داده‌ها

    prompt = f"""
    تو یک دستیار هوشمند فارسی‌زبان هستی.
    وظیفه‌ات اینه که تشخیص بدی سوال کاربر مربوط به کدوم حوزه است (مثلاً قرارداد,فروش متری، لباس، بیمه، مالیات یا خودرو)
    و فقط از داده‌های همان حوزه پاسخ بده.

    اگر سوال مبهم بود یا مشخص نبود مربوط به کدوم موضوعه، محترمانه بپرس برای شفاف‌سازی.

    پاسخ باید:
    - کوتاه، ساده و محاوره‌ای باشه
    - از اطلاعات درست استفاده کنه، نه حدس زدن
    - فقط به موضوع مرتبط جواب بده

    🔸 داده‌های تو:
    {combined_info}

    🔸 سوال کاربر:
    {question}

    پاسخ را خیلی خلاصه، طبیعی و قابل فهم بده.
    """
    answer = await github_llm(prompt)
    return {"answer": answer}


# ----------------------------
# ساخت گراف
# ----------------------------
graph = StateGraph(QAState)
graph.add_node("responder", responder)
graph.set_entry_point("responder")
graph.set_finish_point("responder")

# Compile the graph to make it runnable
graph = graph.compile()


# ----------------------------
# API endpoint
# ----------------------------
@app.post("/ask")
async def ask_question(request: Request):
    body = await request.json()
    question = body.get("question", "").strip()
    if not question:
        return JSONResponse(status_code=400, content={"error": "Question field is required."})

    # اجرای گراف به صورت async
    init_state = QAState({"question": question})
    final_state = await graph.ainvoke(init_state)
    answer = final_state.get("answer", "متأسفانه نتونستم پاسخ بدم.")

    # ذخیره در Supabase
    try:
        supabase.table("chat_logs").insert({
            "question": question,
            "answer": answer
        }).execute()
    except Exception as db_err:
        print("⚠️ DB save error:", db_err)

    return JSONResponse(content={"answer": answer})