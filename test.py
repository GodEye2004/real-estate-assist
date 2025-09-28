import openai

openai.api_key = "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"

response = openai.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "سلام"}]
)

print(response.choices[0].message.content)
