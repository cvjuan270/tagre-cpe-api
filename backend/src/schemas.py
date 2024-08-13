from pydantic import BaseModel
from typing import Optional


class ResponseXmlSign(BaseModel):
    estado: int
    xml: str
    codigo_hash: str
    mensaje: Optional[str]
    external_id: Optional[str]


class ResponseXmlSend(BaseModel):
    estado: int
    mensaje: Optional[str]
    cdr: Optional[str]
    ticket: Optional[str]

class ResponseXmlCdr(BaseModel):
    xml_signed: ResponseXmlSign
    cdr: ResponseXmlSend