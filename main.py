"""Module 5: API Layer.

FastAPI application providing the Agricultural Decision Support System backend endpoints.
Disables Swagger / OpenAPI / ReDoc automatically when running in production (ENVIRONMENT=production).
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, List
from datetime import date
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

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
    CropInfo,
)
from src.config import (
    PROVINCES,
    CROPS,
    PROCESSED_BASELINE_PATH,
    ENVIRONMENT,
    IS_PRODUCTION,
)
from src.baseline_engine import get_baseline_engine
from src.weather_service import get_weather_service
from src.decision_engine import get_decision_engine
from src.rag_service import get_rag_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager: ensures baseline is loaded/generated on startup."""
    print(f"[*] Inicializando API (Ambiente: {ENVIRONMENT.upper()})...")
    if IS_PRODUCTION:
        print("[🔒] Ambiente de PRODUÇÃO detetado: Swagger UI e OpenAPI desativados por segurança.")
    else:
        print("[ℹ️] Ambiente de DESENVOLVIMENTO: Swagger UI disponível em /docs.")
    baseline_engine = get_baseline_engine()
    baseline = baseline_engine.load_baseline()
    prov_count = len(baseline.get("provincias", {}))
    print(f"[✓] Linha de base carregada ({prov_count} províncias do Planalto Central).")
    yield
    print("[*] Encerrando serviço.")


# Security: Disable Swagger, ReDoc, and OpenAPI spec in production
docs_url = None if IS_PRODUCTION else "/docs"
redoc_url = None if IS_PRODUCTION else "/redoc"
openapi_url = None if IS_PRODUCTION else "/openapi.json"

app = FastAPI(
    title="Sistema de Suporte à Decisão Agrícola - Planalto Central de Angola",
    description="Backend e RAG Pipeline para o Planalto Central de Angola (Huambo, Bié e Huíla).",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
)

# Enable CORS for frontend applications
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Monitorização"])
def root_info() -> Dict[str, Any]:
    """Retorna estado e informações gerais da API."""
    return {
        "sistema": "Agricultural Decision Support System - Planalto Central de Angola",
        "versao": "1.0.0",
        "regiao": "Planalto Central (Huambo, Bié, Huíla)",
        "ambiente": ENVIRONMENT,
        "swagger_disponivel": not IS_PRODUCTION,
        "endpoints_principais": {
            "advisory": "POST /api/v1/advisory",
            "provinces": "GET /api/v1/provinces",
            "crops": "GET /api/v1/crops",
            "evaluate": "POST /api/v1/evaluate",
            "baseline": "GET /api/v1/baseline/{provincia}",
            "health": "GET /health",
        },
    }


@app.get("/health", tags=["Monitorização"])
def health_check() -> Dict[str, Any]:
    """Verifica a integridade do serviço, da linha de base NASA e das províncias."""
    baseline_exists = PROCESSED_BASELINE_PATH.exists()
    return {
        "status": "healthy",
        "baseline_ready": baseline_exists,
        "provincias_ativas": list(PROVINCES.keys()),
        "culturas_ativas": list(CROPS.keys()),
        "data_servidor": date.today().isoformat(),
    }


@app.get(
    "/api/v1/provinces",
    response_model=List[ProvinceInfo],
    tags=["Metadados"],
    summary="Listar Províncias",
)
def list_provinces() -> List[ProvinceInfo]:
    """Lista as províncias do Planalto Central, respetivas coordenadas e zonas agroecológicas."""
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


@app.get(
    "/api/v1/crops",
    response_model=List[CropInfo],
    tags=["Metadados"],
    summary="Listar Culturas Agrícolas",
)
def list_crops() -> List[CropInfo]:
    """Lista as culturas suportadas no sistema para preenchimento de seletores no frontend."""
    crops_list = []
    for c_key, c_val in CROPS.items():
        crops_list.append(
            CropInfo(
                id=c_val.get("id", c_key.lower()),
                nome=c_val["name"],
                nome_cientifico=c_val["scientific_name"],
                icone=c_val.get("icon", "🌱"),
                profundidade_sementeira_cm=c_val.get("soil_depth_cm", 5),
                min_chuva_abertura_mm=c_val.get("min_rain_onset_mm", 20.0),
                notas_agronomicas=c_val.get("notes", ""),
            )
        )
    return crops_list


@app.get(
    "/api/v1/baseline/{provincia}",
    tags=["Agroclima"],
    summary="Consultar Linha de Base Histórica",
)
def get_province_baseline(provincia: str) -> Dict[str, Any]:
    """Consulta as matrizes históricas (2000-2024), percentis mensais e tendências de Mann-Kendall."""
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


@app.post(
    "/api/v1/evaluate",
    response_model=DecisionEvaluationResult,
    tags=["Decisão"],
    summary="Avaliação Agroclimática Determinística",
)
def evaluate_decision_only(payload: AdvisoryRequest) -> DecisionEvaluationResult:
    """Executa a avaliação agronómica determinística das regras heurísticas sem síntese LLM."""
    weather_svc = get_weather_service()
    decision_engine = get_decision_engine()

    try:
        weather_data = weather_svc.fetch_weather(
            payload.provincia, payload.data_consulta, payload.municipio
        )
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


@app.post(
    "/api/v1/advisory",
    response_model=AdvisoryResponse,
    tags=["Recomendação"],
    summary="Obter Recomendação Agroclimática Completa (RAG)",
)
def get_agricultural_advisory(payload: AdvisoryRequest) -> AdvisoryResponse:
    """Endpoint Principal: Avalia o período de sementeira e devolve a recomendação formal via RAG."""
    weather_svc = get_weather_service()
    decision_engine = get_decision_engine()
    rag_svc = get_rag_service()

    # 1. Fetch weather with baseline fallback or strategic climatology
    try:
        weather_data = weather_svc.fetch_weather(
            payload.provincia, payload.data_consulta, payload.municipio
        )
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

    # 3. Knowledge synthesis via RAG into formal, objective, and informative Portuguese
    try:
        recomendacao_texto = rag_svc.generate_recommendation(
            provincia=payload.provincia,
            cultura=payload.cultura,
            data_consulta=payload.data_consulta,
            eval_result=eval_result,
        )
    except Exception as e:
        print(f"[!] Erro no RAG: {e}. Utilizando gerador local formal.")
        recomendacao_texto = rag_svc._generate_local_agronomist_synthesis(
            payload.provincia, payload.cultura, payload.data_consulta, eval_result
        )

    # 4. Assemble clean final response strictly matching specification
    response = AdvisoryResponse(
        status=eval_result.status,
        score_confianca=eval_result.score_confianca,
        metricas=AdvisoryMetrics(
            chuva_acumulada_recente_mm=eval_result.metricas.chuva_acumulada_recente_mm,
            humidade_solo_raiz=eval_result.metricas.humidade_solo_raiz,
            previsao_7dias_mm=eval_result.metricas.previsao_7dias_mm,
        ),
        recomendacao_extensao=recomendacao_texto,
    )

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("main:app", host=host, port=port, reload=True)
