import ollama
import anthropic
import gepa

response = ollama.chat(
    model="gemma4:e4b",
    messages=[{"role": "user", "content": "What is photosynthesis? Explain it simply."}]
)
print("✅ Gemma:", response['message']['content'][:100], "...\n")

client = anthropic.Anthropic()
msg = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=50,
    messages=[{"role": "user", "content": "Say hello in 5 words."}]
)
print("✅ Claude:", msg.content[0].text, "\n")

print("✅ GEPA version:", gepa.__version__)
print("\n🎉 Environment ready!")
