from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict
import asyncio
import random
import uuid
import llm

router = APIRouter()

CORRECT_ANSWER_TOKEN = "<<!!CORRECT_ANSWER!!>>"

class RiddleResponse(BaseModel):
    session_id: str
    riddle: str

class RiddleAnswerRequest(BaseModel):
    session_id: str
    answer: str

riddles = [
    {
        "riddle": "With no vowels or repeats, i'm progress,\nAs an abbreviation, I love you too much,\nWrap me around an iterable and I'll track execution,\nFour little letters are all that you need,\nCan you guess which four letters are thee?",
        "answer": "tqdm"
    },
    {
        "riddle": "To speed up I slow down,\nToo much and I'll cease to be,\nNot enough and I'll be lost forever,\nWhat am I?",
        "answer": "satellite"
    }
]

class RiddleSession:
    def __init__(self, riddle: str, answer: str):
        self.riddle = riddle
        self.answer = answer
        self.attempts: List[str] = []

active_riddles: Dict[str, RiddleSession] = {}

@router.get("/riddle")
async def send_riddle():
    session_id = str(uuid.uuid4())
    riddle_data = random.choice(riddles)
    active_riddles[session_id] = RiddleSession(riddle_data["riddle"], riddle_data["answer"])
    return RiddleResponse(session_id=session_id, riddle=riddle_data["riddle"])

@router.post("/riddle-response")
async def answer_riddle(request: RiddleAnswerRequest):
    if request.session_id not in active_riddles:
        raise HTTPException(status_code=404, detail="Invalid session ID")
    
    session = active_riddles[request.session_id]
    session.attempts.append(request.answer)

    async def generate_response():
        if session.answer.lower() in request.answer.lower():
            yield CORRECT_ANSWER_TOKEN
            del active_riddles[request.session_id]  # Clean up the session
            return

        prompt = f"""
        The user was given this riddle: {session.riddle}
        The user's answer is: {request.answer}
        Previous attempts: {', '.join(session.attempts[:-1]) if len(session.attempts) > 1 else 'None'}

        The answer is incorrect. Provide a hint without revealing the answer.
        Be encouraging and maintain a friendly tone.
        """

        messages = [
            {"role": "system", "content": "You are a helpful assistant skilled in riddles."},
            {"role": "user", "content": prompt}
        ]

        async for content in llm.groq_client_chat_completion_stream(messages):
            yield content

    return StreamingResponse(generate_response(), media_type="text/plain")
