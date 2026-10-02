from pydantic import BaseModel


class Model(BaseModel):
    question:str
    user_id:str
    model:str="gemini-2.5-flash"
    conversation_id:int |None=None