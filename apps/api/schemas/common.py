from pydantic import BaseModel


class IdResponse(BaseModel):
    id: str
