"""Pydantic v2 schemas for the Agricultural Decision Support System.

Provides robust validation, strict typing, and comprehensive OpenAPI documentation
for frontend developers, mobile engineers, and data consumers.
"""

from datetime import date
from enum import Enum
from typing import Optional, Dict, Any, List
import unicodedata
from pydantic import BaseModel, Field, field_validator


class AdvisoryStatus(str, Enum):
    """Veredito agronómico determinístico."""
    FAVORAVEL = "FAVORAVEL"
    AGUARDAR = "AGUARDAR"
    DESFAVORAVEL = "DESFAVORAVEL"


class UIHints(BaseModel):
    """Metadados de auxílio para designers e programadores de frontend."""
    cor_status_hex: str = Field(
        ...,
        description="Código de cor hexadecimal recomendado para a badge/card do veredito (ex: #16A34A verde, #D97706 amarelo, #DC2626 vermelho)",
        examples=["#16A34A"]
    )
    rotulo_status: str = Field(
        ...,
        description="Texto amigável e formal para o título da recomendação",
        examples=["Favorável para Semear"]
    )
    icone: str = Field(
        ...,
        description="Emoji ou ícone de estado para enriquecer o componente visual",
        examples=["✅"]
    )
    nivel_urgencia: str = Field(
        ...,
        description="Nível de alerta para acessibilidade e estilização ('sucesso', 'atencao', 'alerta')",
        examples=["sucesso"]
    )


class AdvisoryRequest(BaseModel):
    """Payload de entrada para consulta de orientação de sementeira."""
    provincia: str = Field(
        ...,
        description="Província selecionada pelo agricultor no Planalto Central (Huambo, Bié ou Huíla)",
        examples=["Huambo"]
    )
    cultura: str = Field(
        default="Milho",
        description="Cultura agrícola visada para o plantio (Milho, Feijão ou Soja)",
        examples=["Milho"]
    )
    data_consulta: str = Field(
        default_factory=lambda: date.today().isoformat(),
        description="Data de planeamento no formato YYYY-MM-DD. Se omitida pelo agricultor, o sistema assume a data de hoje.",
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
        
        # Normalize accents for resilient matching (e.g. Bie -> Bié, Huila -> Huíla)
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


class AdvisoryMetrics(BaseModel):
    """Métricas agroclimáticas consolidadas (observadas e previstas)."""
    chuva_acumulada_recente_mm: float = Field(
        ...,
        description="Precipitação acumulada recente nos últimos 3 a 5 dias (mm)",
        examples=[48.2]
    )
    humidade_solo_raiz: float = Field(
        ...,
        description="Nível atual de humidade disponível na camada radicular (fração de 0 a 1)",
        examples=[0.341]
    )
    previsao_7dias_mm: float = Field(
        ...,
        description="Precipitação total acumulada prevista para os próximos 7 dias (mm)",
        examples=[83.4]
    )
    humidade_solo_superficie: Optional[float] = Field(
        None,
        description="Humidade na camada superficial do solo (0-7 cm, fração 0 a 1)",
        examples=[0.404]
    )
    temperatura_max_prevista_c: Optional[float] = Field(
        None,
        description="Temperatura máxima prevista para a próxima semana (°C)",
        examples=[26.1]
    )
    p25_historico_raiz: Optional[float] = Field(
        None,
        description="Limiar P25 histórico de sobrevivência hídrica na raiz para este mês",
        examples=[0.432]
    )
    probabilidade_sementeira_semanal: Optional[float] = Field(
        None,
        description="Probabilidade histórica (%) de sucesso de sementeira nesta semana com base em 25 anos",
        examples=[72.0]
    )


class AdvisoryResponse(BaseModel):
    """Resposta completa do sistema com veredito, métricas, texto RAG e auxílios de UI."""
    status: AdvisoryStatus = Field(
        ...,
        description="Veredito agronómico determinístico ('FAVORAVEL', 'AGUARDAR' ou 'DESFAVORAVEL')",
        examples=["AGUARDAR"]
    )
    score_confianca: int = Field(
        ...,
        ge=0,
        le=100,
        description="Nível de confiança da recomendação em percentagem (0 a 100%)",
        examples=[82]
    )
    metricas: AdvisoryMetrics = Field(
        ...,
        description="Bloco de métricas agroclimáticas fundamentais"
    )
    recomendacao_extensao: str = Field(
        ...,
        description="Texto sintetizado em português formal, simples e sem jargões para apresentação ao agricultor",
        examples=["**AGUARDAR: Recomenda-se aguardar antes de realizar a sementeira de Milho no Huambo...**"]
    )
    ui_hints: Optional[UIHints] = Field(
        None,
        description="Metadados prontos a consumir pelo frontend para estilização de cores, ícones e rótulos"
    )


class DecisionEvaluationResult(BaseModel):
    """Resultado detalhado do motor determinístico (útil para auditoria ou modo offline)."""
    status: AdvisoryStatus
    score_confianca: int
    triggers_ativados: List[str]
    justificacoes_tecnicas: List[str]
    metricas: AdvisoryMetrics
    is_fallback_weather: bool = False
    detalhes_agroclimaticos: Dict[str, Any] = Field(default_factory=dict)


class ProvinceInfo(BaseModel):
    """Informações geográficas e agroecológicas para seletores no frontend."""
    id: str = Field(description="Identificador da província em minúsculas (ex: huambo)", examples=["huambo"])
    nome: str = Field(description="Nome formatado da província", examples=["Huambo"])
    latitude: float = Field(description="Latitude geográfica do centro produtivo", examples=[-12.7761])
    longitude: float = Field(description="Longitude geográfica do centro produtivo", examples=[15.7392])
    altitude_m: int = Field(description="Altitude média em metros acima do nível do mar", examples=[1700])
    zona_agroecologica: str = Field(description="Classificação da zona agroecológica regional", examples=["Planalto Central Tropical de Altitude"])
    icone: str = Field(default="📍", description="Emoji/ícone visual para representação em mapa ou seletor")


class CropInfo(BaseModel):
    """Metadados sobre culturas agrícolas suportadas para preenchimento de dropdowns."""
    id: str = Field(description="Identificador único da cultura (ex: milho)", examples=["milho"])
    nome: str = Field(description="Nome em português comum", examples=["Milho"])
    nome_cientifico: str = Field(description="Nomenclatura botânica científica", examples=["Zea mays"])
    icone: str = Field(description="Emoji representativo para botões ou cartões", examples=["🌽"])
    profundidade_sementeira_cm: int = Field(description="Profundidade recomendada para a colocação da semente (cm)", examples=[5])
    min_chuva_abertura_mm: float = Field(description="Volume mínimo de chuva recente recomendado para plantio (mm)", examples=[20.0])
    notas_agronomicas: str = Field(description="Resumo prático das exigências da planta", examples=["Cultura base de segurança alimentar no Planalto Central."])
