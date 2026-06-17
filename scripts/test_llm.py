import httpx
API_KEY = "sk-..."
prompt = "Hola! esto es una prueba"
try:
        response = httpx.post(
                "http://156.35.160.78:4000/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gemma3:27b",
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                },
                timeout=120,
            )
        print(response)
except Exception as e:
    print(e)