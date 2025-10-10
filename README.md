# Persian Intelligent Q&A System

A sophisticated Persian-language question-answering system powered by Large Language Models (LLMs) and LangGraph, designed to provide accurate, context-aware responses across multiple domains.

##  Features

- **Intelligent Topic Detection**: Automatically identifies the domain of user questions (contracts, sales, clothing, insurance, tax, automotive)
- ** Knowledge-Based Responses**: Utilizes structured JSON knowledge bases for accurate, fact-based answers
- ** LangGraph Workflow**: Implements a state-driven graph architecture for robust question processing
- **Conversation Logging**: Stores all interactions in Supabase for analytics and improvement
- **RESTful API**: FastAPI-powered endpoint for easy integration
- **Persian Language Optimized**: Native Farsi support with natural, conversational responses
- **Flexible LLM Integration**: Modular design allows easy switching between different Large Language Model providers

##  Architecture

```
User Question → FastAPI Endpoint → LangGraph State Machine → Large Language Model → Response
                                                                     ↓
                                                              Supabase Logging
```

### Key Components

- **FastAPI**: High-performance web framework for API endpoints
- **LangGraph**: State machine orchestration for question-answer workflow
- **Large Language Model**: AI inference using GPT-4o-mini (configurable)
- **Supabase**: Database for conversation history and analytics
- **Knowledge Base**: JSON-structured domain-specific information

## Getting Started

### Prerequisites

- Python 3.8+
- API Token for your chosen LLM provider (GitHub Models, OpenAI, etc.)
- Supabase account and credentials

### Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/persian-qa-system.git
cd persian-qa-system
```

2. Install dependencies:

```bash
pip install fastapi uvicorn supabase python-dotenv langgraph httpx
```

3. Create a `.env` file:

```env
GITHUB_TOKEN=your_llm_api_token_here
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

4. Set up your knowledge base: Create JSON files in the `knowledge/` directory:

```
knowledge/
├── contract.json
├── sales.json
├── clothing.json
├── insurance.json
├── tax.json
└── automotive.json
```

Example knowledge file structure:

```json
{
  "topic": "قرارداد",
  "faqs": [
    {
      "question": "قرارداد چیست؟",
      "answer": "قرارداد توافق‌نامه حقوقی بین دو یا چند طرف است."
    }
  ]
}
```

### Running the Application

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

##  API Usage

### Endpoint: POST `/ask`

**Request:**

```json
{
  "question": "قرارداد فروش چیست؟"
}
```

**Response:**

```json
{
  "answer": "قرارداد فروش یک توافق حقوقی است که در آن فروشنده متعهد می‌شود کالا یا خدمتی را در ازای مبلغ مشخصی به خریدار منتقل کند."
}
```

### Example using cURL:

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "بیمه شخص ثالث چیست؟"}'
```

### Example using Python:

```python
import requests

response = requests.post(
    "http://localhost:8000/ask",
    json={"question": "مالیات بر ارزش افزوده چیست؟"}
)
print(response.json())
```

##  Technology Stack

|Technology|Purpose|
|---|---|
|FastAPI|Web framework and API routing|
|LangGraph|State machine and workflow orchestration|
|Large Language Model|AI inference and natural language understanding|
|Supabase|Database and conversation logging|
|httpx|Async HTTP client for LLM API calls|
|python-dotenv|Environment variable management|

##  Large Language Model Integration

The system is designed with a flexible LLM integration that can work with various providers:

- **GitHub Models** (default): GPT-4o-mini via GitHub's inference API
- **OpenAI**: Direct OpenAI API integration
- **Azure OpenAI**: Enterprise-grade deployment
- **Anthropic Claude**: Alternative LLM provider
- **Local Models**: Ollama, LM Studio, or custom endpoints

### Switching LLM Providers

The `github_llm()` function can be easily modified to work with any LLM provider. Simply update the endpoint URL and authentication:

```python
# Example: Switch to OpenAI
async def openai_llm(prompt: str) -> str:
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}]
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload
        )
    return response.json()["choices"][0]["message"]["content"]
```

## Database Schema

The system logs conversations to Supabase with the following structure:

```sql
CREATE TABLE chat_logs (
  id SERIAL PRIMARY KEY,
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
```

## 🎯 Use Cases

- **Customer Support**: Automated responses for common questions
- **Knowledge Management**: Centralized information retrieval
- **Educational Tools**: Persian language learning and information access
- **Business Automation**: Contract, sales, and insurance inquiries
- **Legal Assistance**: Quick answers to legal and regulatory questions

##  Configuration

### LLM Parameters

Adjust the Large Language Model API call in `github_llm()`:

```python
payload = {
    "model": "openai/gpt-4o-mini",
    "messages": [{"role": "user", "content": prompt}],
    "temperature": 0.3,  # Lower = more deterministic
}
```

### CORS Settings

Modify allowed origins in the FastAPI middleware:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

##  Security Best Practices

- Store sensitive tokens in `.env` file (never commit to Git)
- Use HTTPS in production
- Implement rate limiting for API endpoints
- Validate and sanitize user inputs
- Restrict CORS origins to trusted domains

##  Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

##  License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

##  Acknowledgments

- **LLM Providers**: For making AI accessible through various platforms
- **LangGraph**: For elegant state machine orchestration
- **FastAPI**: For high-performance API development
- **Supabase**: For reliable database services

## Contact

For questions or support, please open an issue or contact mohammadg248015@gmail.com

---

