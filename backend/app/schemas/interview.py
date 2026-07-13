from pydantic import BaseModel


class AnswerSubmit(BaseModel):
    answer_text: str
