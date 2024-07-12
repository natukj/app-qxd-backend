from tenacity import retry, wait_random_exponential, stop_after_attempt
import httpx
from groq import AsyncGroq
from typing import List, Dict, AsyncGenerator
import os
client = AsyncGroq()
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

async def groq_client_chat_completion_stream(
    messages: List[Dict[str, str]], 
    model: str = "llama3-70b-8192"
) -> AsyncGenerator[str, None]:
    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=600,
            stream=True
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

    except Exception as e:
        print(f"Groq Streaming Request failed with exception: {e}")
        raise

async def groq_client_chat_completion_request(messages, model="llama3-8b-8192"):
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=200,
        )
        return response
    except Exception as e:
        print(f"Groq Request failed with exception: {e}")
        raise

@retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
async def groq_chat_completion_request(messages, tools=None, tool_choice=None, json_mode=False, model="mixtral-8x7b-32768"):
    """llama3-8b-8192, llama3-70b-8192, mixtral-8x7b-32768"""
    headers = {
        "Authorization": f"Bearer " + GROQ_API_KEY,
        "Content-Type": "application/json",
    }

    json_data = {
        "messages": messages,
        "model": model
    }
    if json_mode:
        json_data.update({"response_format": {"type": "json_object"}})
    if tools is not None:
        json_data.update({"tools": tools})
    if tool_choice is not None:
        json_data.update({"tool_choice": tool_choice})

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=json_data,
                timeout=60
            )
            response.raise_for_status()
            return response
        except httpx.ReadTimeout as e:
            print("Groq Request timed out.")
            print(f"Exception: {e}")
            raise
        except httpx.HTTPStatusError as e:
            print(f"Groq Request failed with status code: {e.response.status_code}")
            print(f"Exception: {e}")
            raise
        except Exception as e:
            print("Groq Unable to generate ChatCompletion response.")
            print(f"Exception: {e}")
            raise