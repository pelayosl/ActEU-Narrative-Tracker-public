import httpx
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("LLM_API_KEY")


models_json={
    "data": [
        {
            "id": "qwen3.6:27b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "deepseek-v2:16b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "qwen3-vl:8b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "gpt-oss:20b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "gemma3:12b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "qwen3.5:9b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "qwen3-vl:30b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "llama3.2:1b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "llama3.2:latest",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "deepseek-coder:6.7b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "deepseek-r1:7b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "deepseek-r1:14b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "glm-ocr:latest",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "gemma4:12b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "qwen2.5-coder:1.5b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "codegemma:7b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "qwen2.5-coder:7b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "qwen2.5-coder:14b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "qwen3.5:27b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "gemma3:27b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "deepseek-coder:1.3b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "llama3.2:3b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "qwen3.5:2b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "qwen3.5:4b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "qwen2.5:7b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "qwen3:8b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "qwen2.5-coder:3b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "codegemma:2b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "qwen2.5-coder:0.5b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "llama3.1:8b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "codellama:7b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "codellama:13b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "hf.co/mixedbread-ai/mxbai-embed-large-v1:latest",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "gemma4:e4b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "gemma4:31b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "qwen3.6:35b",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        },
        {
            "id": "codellama:13b-instruct",
            "object": "model",
            "created": 1677610602,
            "owned_by": "openai"
        }
    ],
    "object": "list"
}

def test_models():
    for model_info in models_json["data"]:
        model_name = model_info["id"]

        try:
            response = httpx.post(
                "http://156.35.160.78:4000/v1/chat/completions",
                headers={"Authorization": f"Bearer {API_KEY}"},
                json={
                    "model": model_name,
                    "messages": [
                        {"role": "user", "content": "Hi"}
                    ],
                },
                timeout=30,
            )

            if response.status_code == 200:
                print(f"✅ {model_name}")
            else:
                print(f"❌ {model_name} ({response.status_code})")

        except Exception as e:
            print(f"❌ {model_name} ({e})")

def test_specific_model(model):
    try:
            response = httpx.post(
                "http://156.35.160.78:4000/v1/chat/completions",
                headers={"Authorization": f"Bearer {API_KEY}"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "user", "content": "Talk to me (briefly) about your model and its benchmark performance."}
                    ],
                },
                timeout=120,
            )

            if response.status_code == 200:
                print(response.json())
            else:
                print(f"❌ {response.json()}")

    except Exception as e:
            print(f"❌ {e}")

test_specific_model("gemma4:26b")