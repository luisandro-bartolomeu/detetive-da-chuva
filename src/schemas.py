"""Pydantic v2 schemas for the Agricultural Decision Support System.
"""

from datetime import date
from enum import Enum
from typing import Optional, Dict, Any, List
import unicodedata
from pydantic import BaseModel, Field, field_validator


class AdvisoryStatus(str, Enum):
    FAVORAVEL = "FAVORAVEL"
    AGUARDAR = "AGUARDAR"
    DESFAVORAVEL = "DESFAVORAVEL"


class AdvisoryRequest(BaseModel):
    provincia: str = Field(
        ...,
        description="Província selecionada pelo agricultor (Huambo, Bié ou Huíla)",
        examples=["Huambo"]
    )
    cultura: str = Field(
        default="Milho",
        description="Cultura agrícola visada (ex: Milho, Feijão, Soja)",
        examples=["Milho"]
    )
    data_consulta: str = Field(
        default_factory=lambda: date.today().isoformat(),
        description="Data de consulta no formato YYYY-MM-DD. Se omitida, utiliza a data de hoje.",
        examples=["2026-11-12"]
    )

    @field_validator("data_consulta", mode="before")
    @classmethod
    def set_default_data_consulta(cls, v: Any) -> str:
        if v is None or not str(v).strip():
            return date.today().isoformat()
        return str(v).strip()

    @field_validator("provincia")
    @classmethod
    def validate_provincia(cls, v: str) -> str:
        if not v or not str(v).strip():
            raise ValueError("O agricultor deve selecionar a província (Huambo, Bié ou Huíla).")
        
        # Normalize accents for resilient matching
        raw = v.strip()
        normalized = unicodedata.normalize("NFKD", raw).encode("ASCII", "ignore").decode("utf-8").strip().title()
        
        mapping = {
            "Bie": "Bié",
            "Huambo": "Huambo",
            "Huila": "Huíla",
        }
        
        if normalized in mapping:
            return mapping[normalized]
            
        raise ValueError(
            f"Província '{v}' não suportada. O agricultor deve escolher uma das seguintes províncias: Huambo, Bié ou Huíla."
        )

    @field_validator("cultura")
    @classmethod
    def validate_cultura(cls, v: str) -> str:
        clean = v.strip().title()
        mapping = {
            "Milho": "Milho",
            "Feijao": "Feijão",
            "Feijão": "Feijão",
            "Soja": "Soja",
        }
        return mapping.get(clean, clean)


class AdvisoryMetrics(BaseModel):
    chuva_acumulada_recente_mm: float = Field(
        ...,
        description="Chuva acumulada nos últimos 3 a 5 dias (mm)"
    )
    humidade_solo_raiz: float = Field(
        ...,
        description="Humidade atual estimada na zona radicular (0 a 1)"
    )
    previsao_7dias_mm: float = Field(
        ...,
        description="Precipitação total prevista para os próximos 7 dias (mm)"
    )
    # Optional supplementary metrics for rich debugging/dashboards
    humidade_solo_superficie: Optional[float] = Field(
        None,
        description="Humidade na camada superficial do solo (0-7 cm)"
    )
    temperatura_max_prevista_c: Optional[float] = Field(
        None,
        description="Temperatura máxima prevista para a próxima semana (°C)"
    )
    p25_historico_raiz: Optional[float] = Field(
        None,
        description="Limiar P25 histórico de humidade radicular para o mês"
    )
    probabilidade_sementeira_semanal: Optional[float] = Field(
        None,
        description="Probabilidade histórica (%) de condições favoráveis para a semana"
    )


class AdvisoryResponse(BaseModel):
    status: AdvisoryStatus = Field(
        ...,
        description="Veredito agronómico determinístico (FAVORAVEL, AGUARDAR, DESFAVORAVEL)"
    )
    score_confianca: int = Field(
        ...,
        ge=0,
        le=100,
        description="Pontuação objetiva de confiança da recomendação (0-100%)"
    )
    metricas: AdvisoryMetrics = Field(
        ...,
        description="Métricas agroclimáticas observadas e previstas"
    )
    recomendacao_extensao: str = Field(
        ...,
        description="Texto sintetizado em português empático e sem jargões para o agricultor"
    )


class DecisionEvaluationResult(BaseModel):
    status: AdvisoryStatus
    score_confianca: int
    triggers_ativados: List[str]
    justificacoes_tecnicas: List[str]
    metricas: AdvisoryMetrics
    is_fallback_weather: bool = False
    detalhes_agroclimaticos: Dict[str, Any] = Field(default_factory=dict)


class ProvinceInfo(BaseModel):
    id: str
    nome: str
    latitude: float
    longitude: float
    altitude_m: int
    zona_agroecologica: str
