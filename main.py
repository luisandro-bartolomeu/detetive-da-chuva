"""Module 5: API Layer.

FastAPI application providing the Agricultural Decision Support System endpoints,
specifically the primary advisory endpoint: POST /api/v1/advisory.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.schemas import (
    AdvisoryRequest,
    AdvisoryResponse,
    AdvisoryMetrics,
    DecisionEvaluationResult,
    ProvinceInfo,
)
from src.config import PROVINCES, CROPS, PROCESSED_BASELINE_PATH
from src.baseline_engine import get_baseline_engine
from src.weather_service import get_weather_service
from src.decision_engine import get_decision_engine
from src.rag_service import get_rag_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager: ensures baseline is loaded/generated on startup."""
    print("[*] Inicializando Sistema de Suporte à Decisão Agrícola...")
    baseline_engine = get_baseline_engine()
    baseline = baseline_engine.load_baseline()
    prov_count = len(baseline.get("provincias", {}))
    print(f"[✓] Linha de base carregada com sucesso ({prov_count} províncias do Planalto Central).")
    yield
    print("[*] Encerrando serviço.")


app = FastAPI(
    title="Agricultural Decision Support System API (Angola)",
    description=(
        "Sistema de Apoio à Decisão Agrícola e Pipeline RAG para o Planalto Central de Angola "
        "(Huambo, Bié e Huíla). Avalia aptidão agroclimática para sementeira (milho, feijão, soja) "
        "com base em dados históricos da NASA POWER (2000-2024), meteorologia em tempo real Open-Meteo "
        "e síntese via RAG em português compreensível para os agricultores."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for frontend integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Geral"])
def root_info() -> Dict[str, Any]:
    """Informações e estado geral da API."""
    return {
        "sistema": "Agricultural Decision Support System - Planalto Central de Angola",
        "versao": "1.0.0",
        "regiao": "Planalto Central (Huambo, Bié, Huíla)",
        "culturas_suportadas": list(CROPS.keys()),
        "endpoints_principais": {
            "advisory": "/api/v1/advisory",
            "evaluate": "/api/v1/evaluate",
            "provinces": "/api/v1/provinces",
            "baseline": "/api/v1/baseline/{provincia}",
            "docs": "/docs",
        },
    }


@app.get("/health", tags=["Geral"])
def health_check() -> Dict[str, Any]:
    """Verificação de integridade do sistema e dos ficheiros de dados."""
    baseline_exists = PROCESSED_BASELINE_PATH.exists()
    return {
        "status": "healthy",
        "baseline_ready": baseline_exists,
        "provincias_ativas": list(PROVINCES.keys()),
    }


@app.get("/api/v1/provinces", response_model=List[ProvinceInfo], tags=["Agroclima"])
def list_provinces() -> List[ProvinceInfo]:
    """Lista as províncias suportadas no Planalto Central e suas características."""
    result = []
    for p_name, p_data in PROVINCES.items():
        result.append(
            ProvinceInfo(
                id=p_data["id"],
                nome=p_data["name"],
                latitude=p_data["latitude"],
                longitude=p_data["longitude"],
                altitude_m=p_data["elevation_m"],
                zona_agroecologica=p_data["agroecological_zone"],
            )
        )
    return result


@app.get("/api/v1/baseline/{provincia}", tags=["Agroclima"])
def get_province_baseline(provincia: str) -> Dict[str, Any]:
    """Consulta as matrizes históricas completas (2000-2024) para uma província."""
    engine = get_baseline_engine()
    baseline = engine.load_baseline()

    # Search province
    for p_key, p_val in baseline.get("provincias", {}).items():
        if p_key.lower() == provincia.lower() or p_val.get("id") == provincia.lower():
            return p_val

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Província '{provincia}' não encontrada. Províncias suportadas: {list(PROVINCES.keys())}",
    )


@app.post("/api/v1/evaluate", response_model=DecisionEvaluationResult, tags=["Decisão"])
def evaluate_decision_only(payload: AdvisoryRequest) -> DecisionEvaluationResult:
    """Executa apenas a avaliação técnica determinística (sem geração LLM)."""
    weather_svc = get_weather_service()
    decision_engine = get_decision_engine()

    try:
        weather_data = weather_svc.fetch_weather(payload.provincia, payload.data_consulta)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    try:
        eval_result = decision_engine.evaluate(
            provincia=payload.provincia,
            cultura=payload.cultura,
            data_consulta=payload.data_consulta,
            weather_data=weather_data,
        )
        return eval_result
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.post("/api/v1/advisory", response_model=AdvisoryResponse, tags=["Recomendação"])
def get_agricultural_advisory(payload: AdvisoryRequest) -> AdvisoryResponse:
    """Endpoint Principal: Avalia o período de sementeira e devolve recomendação RAG completa."""
    weather_svc = get_weather_service()
    decision_engine = get_decision_engine()
    rag_svc = get_rag_service()

    # 1. Fetch real-time weather with baseline fallback
    try:
        weather_data = weather_svc.fetch_weather(payload.provincia, payload.data_consulta)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Província inválida: {payload.provincia}. Províncias válidas: {list(PROVINCES.keys())}"
        )

    # 2. Rule-based evaluation against historical baseline
    try:
        eval_result = decision_engine.evaluate(
            provincia=payload.provincia,
            cultura=payload.cultura,
            data_consulta=payload.data_consulta,
            weather_data=weather_data,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro durante avaliação agroclimática: {str(e)}"
        )

    # 3. Knowledge synthesis via RAG into empathetic Angolan Portuguese
    try:
        recomendacao_texto = rag_svc.generate_recommendation(
            provincia=payload.provincia,
            cultura=payload.cultura,
            data_consulta=payload.data_consulta,
            eval_result=eval_result,
        )
    except Exception as e:
        print(f"[!] Erro no RAG: {e}. Utilizando gerador local.")
        recomendacao_texto = rag_svc._generate_local_agronomist_synthesis(
            payload.provincia, payload.cultura, eval_result
        )

    # 4. Assemble final response conforming strictly to specification
    response = AdvisoryResponse(
        status=eval_result.status,
        score_confianca=eval_result.score_confianca,
        metricas=AdvisoryMetrics(
            chuva_acumulada_recente_mm=eval_result.metricas.chuva_acumulada_recente_mm,
            humidade_solo_raiz=eval_result.metricas.humidade_solo_raiz,
            previsao_7dias_mm=eval_result.metricas.previsao_7dias_mm,
            humidade_solo_superficie=eval_result.metricas.humidade_solo_superficie,
            temperatura_max_prevista_c=eval_result.metricas.temperatura_max_prevista_c,
            p25_historico_raiz=eval_result.metricas.p25_historico_raiz,
            probabilidade_sementeira_semanal=eval_result.metricas.probabilidade_sementeira_semanal,
        ),
        recomendacao_extensao=recomendacao_texto,
    )

    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
