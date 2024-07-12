from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import Dict, List, Optional
import random
import string
import json
import asyncio
import llm

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class ChatMessage(BaseModel):
    content: str
    chatId: Optional[str] = None

class Message(BaseModel):
    id: str
    content: str
    createdAt: str

class ReferenceContent(BaseModel):
    id: str
    content: str
    title: str

class ChatResponse(BaseModel):
    aiResponse: Message
    chatId: str
    enumeration_mapping: Dict[str, str]
    references: Dict[str, ReferenceContent]

def generate_id():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))

async def stream_ai_response(ai_content: str, chat_response: ChatResponse):
    words = ai_content.split()
    for word in words:
        yield word + " "
        await asyncio.sleep(0.01)  # Simulate delay between words
    
    # Send the final JSON response
    chat_response.aiResponse.content = ""  # Clear content as it's been streamed
    yield "\n" + json.dumps(chat_response.model_dump())

async def generate_response(chat_response: ChatResponse):
    prompt = f"""
    Please output the following but use the '[^1]' for the references, making sure to include the footnote at the end of the document eg '[^1]: 40-880(2A)':
    The Tax Income Assessment Act 1997 (Australia) provides several provisions and concessions for small business owners or self-employed individuals, which are outlined in Division 328 of the Act. These provisions include the following key concessions and rules:

    1. **Immediate Deductibility for Small Business Start-up Expenses**: Small business entities can immediately deduct certain start-up expenses under Subsection 40-880(2A) of the Act ([40-880(2A)](ref:1)).

    2. **Capital Gains Tax (CGT) Concessions**: Small business entities can benefit from various CGT concessions, including:
       - 15-year asset exemption ([152-B](ref:2))
       - 50% active asset reduction ([152-B](ref:2))
       - Retirement exemption ([152-B](ref:2))
       - Roll-over relief ([152-B](ref:2))

    3. **Simpler Depreciation Rules**: Small business entities can use simpler depreciation rules under ([328-D](ref:3)). For example, they can pool depreciating assets and apply a general small business pool deduction formula.

    4. **Simplified Trading Stock Rules**: Small business entities can choose not to account for changes in the value of trading stock if the difference between the opening and closing stock is $5,000 or less ([328-210](ref:4)).

    5. **Small Business Income Tax Offset**: Small business entities can claim a tax offset under ([328-E](ref:5)). This offset is calculated as 16% of the total net small business income for the income year, capped at $1,000.

    6. **Restructures of Small Businesses**: Small business entities can restructure their business without triggering immediate tax consequences, provided certain conditions are met ([328-F](ref:6)).
    """

    messages = [
        {"role": "system", "content": "You are a helpful assistant skilled in markdown."},
        {"role": "user", "content": prompt}
    ]
    all_content = ""
    async for content in llm.groq_client_chat_completion_stream(messages):
        all_content += content
        yield content
    print(all_content)
    yield "\n" + json.dumps(chat_response.model_dump())

@router.post("/{project_id}")
async def chat(project_id: str, message: ChatMessage, token: str = Depends(oauth2_scheme)):
    chat_id = message.chatId or generate_id()

    print(f"Project ID: {project_id}, Chat ID: {chat_id}, Message: {message.content}")

    # Simulated AI response
    ai_content = """The Tax Income Assessment Act 1997 (Australia) provides several provisions and concessions for small business owners or self-employed individuals, which are outlined in Division 328 of the Act. These provisions include the following key concessions and rules:

    1. **Immediate Deductibility for Small Business Start-up Expenses**: Small business entities can immediately deduct certain start-up expenses under Subsection 40-880(2A) of the Act ([40-880(2A)](ref:1)).

    2. **Capital Gains Tax (CGT) Concessions**: Small business entities can benefit from various CGT concessions, including:
       - 15-year asset exemption ([Subdivision 152-B](ref:2))
       - 50% active asset reduction ([Subdivision 152-B](ref:2))
       - Retirement exemption ([Subdivision 152-B](ref:2))
       - Roll-over relief ([Subdivision 152-B](ref:2))

    3. **Simpler Depreciation Rules**: Small business entities can use simpler depreciation rules under ([Subdivision 152-C](ref:3)). For example, they can pool depreciating assets and apply a general small business pool deduction formula.

    4. **Simplified Trading Stock Rules**: Small business entities can choose not to account for changes in the value of trading stock if the difference between the opening and closing stock is $5,000 or less ([Subdivision 328-E](ref:5)).

    5. **Small Business Income Tax Offset**: Small business entities can claim a tax offset under ([Subdivision 328-F](ref:6)). This offset is calculated as 16% of the total net small business income for the income year, capped at $1,000.

    6. **Restructures of Small Businesses**: Small business entities can restructure their business without triggering immediate tax consequences, provided certain conditions are met ([Subdivision 328-G](ref:6)).


    ## Footnote

    A note[^1]

    [^1]: Big note."""

    ai_response = Message(
        id=generate_id(),
        content=ai_content,
        createdAt="2023-06-01T12:01:00Z",
    )

    # Simulated enumeration mapping
    enumeration_mapping = {
        '1': '40-880(2A)',
        '2': '152-B',
        '3': '328-D',
        '4': '328-210',
        '5': '328-E',
        '6': '328-F'
    }

    # Simulated reference contents
    reference_contents = {
        '40-880(2A)': ReferenceContent(
            id='40-880(2A)',
            content="A *start-up expense* is deductible to the extent that it is incurred in getting a *business* that is *small business entity* started if it is incurred: (a) in the income year in which the business starts; or (b) in the income year preceding the one in which the business starts and in anticipation of the business starting.",
            title="Immediate deductibility for certain start-up expenses"
        ),
        '152-B': ReferenceContent(
            id='152-B',
            content="You disregard a capital gain if: (a) you are a CGT small business entity or you satisfy the maximum net asset value test; and (b) you have continuously owned the CGT asset for at least 15 years; and (c) if you are an individual, at the time of the CGT event, you are 55 years old or older and the event happens in connection with your retirement, or you are permanently incapacitated.",
            title="Small business 15-year exemption"
        ),
        '328-D': ReferenceContent(
            id='328-D',
            content="This Subdivision provides for simpler depreciation rules for certain depreciating assets of small business entities.",
            title="Simpler depreciation rules"
        ),
        '328-210': ReferenceContent(
            id='328-210',
            content="The deduction for the income year for the general small business pool is the sum of: (a) 15% of the opening pool balance for the year; and (b) 15% of the taxable purpose proportion of the cost of any assets you added to the pool during the year; and (c) 2.5% of the taxable purpose proportion of the cost of any assets you added to the pool during the last 6 months of the income year, if you started to use them, or installed them ready for use, for a taxable purpose during that period.",
            title="Small business pool deduction formula"
        ),
        '328-E': ReferenceContent(
            id='328-E',
            content="If you are a small business entity, you can choose not to account for changes in the value of your trading stock for an income year if the difference between the value of your opening stock and a reasonable estimate of your closing stock is $5,000 or less.",
            title="Simplified trading stock rules"
        ),
        '328-F': ReferenceContent(
            id='328-F',
            content="An entity is entitled to a tax offset for an income year if: (a) the entity is a small business entity for the income year; or (b) the entity is not carrying on a business and has an aggregated turnover of less than $5 million for the income year.",
            title="Small business income tax offset"
        ),
    }

    chat_response = ChatResponse(
        aiResponse=ai_response,
        chatId=chat_id,
        enumeration_mapping=enumeration_mapping,
        references=reference_contents
    )

    #return StreamingResponse(stream_ai_response(ai_content, chat_response), media_type="text/plain")
    return StreamingResponse(generate_response(chat_response), media_type="text/plain")




# from fastapi import APIRouter, Depends, HTTPException
# from fastapi.security import OAuth2PasswordBearer
# from pydantic import BaseModel
# from typing import Dict, List, Optional
# import random
# import string

# router = APIRouter()

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# class ChatMessage(BaseModel):
#     content: str
#     chatId: Optional[str] = None

# class Message(BaseModel):
#     id: str
#     content: str
#     createdAt: str

# class ReferenceContent(BaseModel):
#     id: str
#     content: str
#     title: str

# class ChatResponse(BaseModel):
#     aiResponse: Message
#     chatId: str
#     enumeration_mapping: Dict[str, str]
#     references: Dict[str, ReferenceContent]

# def generate_id():
#     return ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))

# @router.post("/{project_id}", response_model=ChatResponse)
# async def chat(project_id: str, message: ChatMessage, token: str = Depends(oauth2_scheme)):
#     # Simulate creating a new chat or using an existing one
#     chat_id = message.chatId or generate_id()

#     print(f"Project ID: {project_id}, Chat ID: {chat_id}, Message: {message.content}")

#     # Simulated AI response
#     ai_content = """The Tax Income Assessment Act 1997 (Australia) provides several provisions and concessions for small business owners or self-employed individuals, which are outlined in Division 328 of the Act. These provisions include the following key concessions and rules:

# 1. **Immediate Deductibility for Small Business Start-up Expenses**: Small business entities can immediately deduct certain start-up expenses under Subsection 40-880(2A) of the Act ([40-880(2A)](ref:1)).

# 2. **Capital Gains Tax (CGT) Concessions**: Small business entities can benefit from various CGT concessions, including:
#    - 15-year asset exemption ([Subdivision 152-B](ref:2))
#    - 50% active asset reduction ([Subdivision 152-B](ref:2))
#    - Retirement exemption ([Subdivision 152-B](ref:2))
#    - Roll-over relief ([Subdivision 152-B](ref:2))

# 3. **Simpler Depreciation Rules**: Small business entities can use simpler depreciation rules under ([Subdivision 152-C](ref:3)). For example, they can pool depreciating assets and apply a general small business pool deduction formula.

# 4. **Simplified Trading Stock Rules**: Small business entities can choose not to account for changes in the value of trading stock if the difference between the opening and closing stock is $5,000 or less ([Subdivision 328-E](ref:5)).

# 5. **Small Business Income Tax Offset**: Small business entities can claim a tax offset under ([Subdivision 328-F](ref:6)). This offset is calculated as 16% of the total net small business income for the income year, capped at $1,000.

# 6. **Restructures of Small Businesses**: Small business entities can restructure their business without triggering immediate tax consequences, provided certain conditions are met ([Subdivision 328-G](ref:6)).


# ## Footnote

# A note[^1]

# [^1]: Big note."""

#     ai_response = Message(
#         id=generate_id(),
#         content=ai_content,
#         role="assistant",
#         createdAt="2023-06-01T12:01:00Z",
#     )

#     # Simulated enumeration mapping
#     enumeration_mapping = {
#         '1': '40-880(2A)',
#         '2': '152-B',
#         '3': '328-D',
#         '4': '328-210',
#         '5': '328-E',
#         '6': '328-F'
#     }

#     # Simulated reference contents
#     reference_contents = {
#         '40-880(2A)': ReferenceContent(
#             id='40-880(2A)',
#             content="A *start-up expense* is deductible to the extent that it is incurred in getting a *business* that is *small business entity* started if it is incurred: (a) in the income year in which the business starts; or (b) in the income year preceding the one in which the business starts and in anticipation of the business starting.",
#             title="Immediate deductibility for certain start-up expenses"
#         ),
#         '152-B': ReferenceContent(
#             id='152-B',
#             content="You disregard a capital gain if: (a) you are a CGT small business entity or you satisfy the maximum net asset value test; and (b) you have continuously owned the CGT asset for at least 15 years; and (c) if you are an individual, at the time of the CGT event, you are 55 years old or older and the event happens in connection with your retirement, or you are permanently incapacitated.",
#             title="Small business 15-year exemption"
#         ),
#         '328-D': ReferenceContent(
#             id='328-D',
#             content="This Subdivision provides for simpler depreciation rules for certain depreciating assets of small business entities.",
#             title="Simpler depreciation rules"
#         ),
#         '328-210': ReferenceContent(
#             id='328-210',
#             content="The deduction for the income year for the general small business pool is the sum of: (a) 15% of the opening pool balance for the year; and (b) 15% of the taxable purpose proportion of the cost of any assets you added to the pool during the year; and (c) 2.5% of the taxable purpose proportion of the cost of any assets you added to the pool during the last 6 months of the income year, if you started to use them, or installed them ready for use, for a taxable purpose during that period.",
#             title="Small business pool deduction formula"
#         ),
#         '328-E': ReferenceContent(
#             id='328-E',
#             content="If you are a small business entity, you can choose not to account for changes in the value of your trading stock for an income year if the difference between the value of your opening stock and a reasonable estimate of your closing stock is $5,000 or less.",
#             title="Simplified trading stock rules"
#         ),
#         '328-F': ReferenceContent(
#             id='328-F',
#             content="An entity is entitled to a tax offset for an income year if: (a) the entity is a small business entity for the income year; or (b) the entity is not carrying on a business and has an aggregated turnover of less than $5 million for the income year.",
#             title="Small business income tax offset"
#         ),
#     }

#     return ChatResponse(
#         aiResponse=ai_response,
#         chatId=chat_id,
#         enumeration_mapping=enumeration_mapping,
#         references=reference_contents
#     )
