from __future__ import annotations

from pydantic import BaseModel, Field


class TransacaoBase(BaseModel):
    valor: float = Field(..., description="Valor da transação.")
    data: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Data no formato YYYY-MM-DD.",
    )
    hora: str = Field(
        ...,
        pattern=r"^\d{2}:\d{2}(:\d{2})?$",
        description="Hora no formato HH:MM ou HH:MM:SS.",
    )
    dia_semana: str = Field(..., min_length=1, max_length=20)
    categoria: str = Field(..., min_length=1, max_length=100)
    conta: str = Field(..., min_length=1, max_length=100)
    cidade: str = Field(..., min_length=1, max_length=100)
    estado: str = Field(..., min_length=1, max_length=100)
    pais: str = Field(..., min_length=1, max_length=100)
    latitude: float | None = Field(None, description="Latitude.")
    longitude: float | None = Field(None, description="Longitude.")
    tipo_transacao: str = Field(..., min_length=1, max_length=50)
    dispositivo: str = Field(..., min_length=1, max_length=100)
    estabelecimento: str = Field(..., min_length=1, max_length=255)
    tentativas: int = Field(..., ge=0)
    ip_origem: str = Field(..., min_length=1, max_length=45)


class TransacaoCreate(TransacaoBase):
    pass


class TransacaoUpdate(TransacaoBase):
    pass


class TransacaoResponse(TransacaoBase):
    id: int = Field(..., description="ID da transação.")
    is_fraude: bool = Field(..., description="Indica se a transação é fraudulenta.")