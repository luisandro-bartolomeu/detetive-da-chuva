"""Module 5: API Layer.

FastAPI application providing the Agricultural Decision Support System endpoints,
specifically the primary advisory endpoint: POST /api/v1/advisory, with an interactive,
production-ready Swagger UI documentation setup.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import date
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse

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
from src.config import (
    PROVINCES,
    CROPS,
    PROCESSED_BASELINE_PATH,
    SERVER_HOST,
    SERVER_PORT,
)
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


# OpenAPI Tag Metadata for Production Documentation
TAGS_METADATA = [
    {
        "name": "Recomendação & RAG",
        "description": "Endpoint principal do sistema. Integra meteorologia em tempo real (Open-Meteo), "
                       "a linha de base climatológica da NASA POWER (2000-2024), o motor determinístico "
                       "de decisão agronómica e síntese de linguagem natural via Google Gemini.",
    },
    {
        "name": "Decisão Heurística",
        "description": "Avaliação técnica determinística pura dos gatilhos agroclimáticos "
                       "(reserva radicular P25, chuva recente >= 20mm, risco de veranico) sem chamada ao LLM.",
    },
    {
        "name": "Linha de Base NASA POWER",
        "description": "Consulta às matrizes agroclimáticas pré-computadas de 25 anos: "
                       "percentis mensais de humidade, curvas semanais de sementeira e testes de Mann-Kendall.",
    },
    {
        "name": "Províncias & Agroecologia",
        "description": "Informações geográficas e zonas agroecológicas das províncias suportadas "
                       "(Huambo, Bié e Huíla).",
    },
    {
        "name": "Monitorização & Sistema",
        "description": "Verificação de integridade operacional, estado dos ficheiros e conectividade.",
    },
]

# Swagger UI interactive settings
SWAGGER_UI_PARAMETERS = {
    "defaultModelsExpandDepth": 2,
    "defaultModelExpandDepth": 2,
    "docExpansion": "list",
    "displayRequestDuration": True,
    "filter": True,
    "showExtensions": True,
    "showCommonExtensions": True,
    "syntaxHighlight.theme": "monokai",
    "tryItOutEnabled": True,
}

app = FastAPI(
    title="Sistema de Suporte à Decisão Agrícola - Planalto Central de Angola",
    description=r"""
## 🌽 Plataforma Agroclimática e Pipeline RAG para Pequenos Agricultores

Bem-vindo à documentação interativa da API do **Sistema de Suporte à Decisão Agrícola** desenvolvido especificamente para o **Planalto Central de Angola (Huambo, Bié e Huíla)**.

---

### 🚀 Funcionalidades Principais:
1. **Escolha da Província pelo Agricultor:** O agricultor seleciona a província de interesse (`Huambo`, `Bié` ou `Huíla`) e a cultura pretendida (`Milho`, `Feijão` ou `Soja`). A data é opcional (assume a data atual por defeito).
2. **Avaliação Científica Rigorosa:** Combina 25 anos de dados diários de satélite da **NASA POWER (2000-2024)** com dados meteorológicos e previsões a 7 dias da **Open-Meteo**.
3. **Motor Heurístico Determinístico:** Aplica limiares objetivos de reserva radicular ($P_{25}$), gatilhos de chuva recente ($\ge 20\\text{ mm}$) e deteção precoce de risco de veranico/falso início das chuvas.
4. **Síntese RAG via Google Gemini:** Traduz as métricas complexas numa recomendação **formal, simples e informativa**, sem termos estatísticos, estruturada em:
   * **Veredito Claro:** `FAVORÁVEL`, `AGUARDAR` ou `NÃO PLANTAR`
   * **2 a 3 Justificações Objetivas**
   * **Recomendação Prática de Campo** (teste do torrão na palma da mão a 5 cm)

---
*Para testar os endpoints, selecione um dos cenários predefinidos abaixo e clique em **Execute**.*
""",
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=TAGS_METADATA,
    docs_url="/docs",
    redoc_url="/redoc",
    swagger_ui_parameters=SWAGGER_UI_PARAMETERS,
)

# Enable CORS for frontend applications
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Monitorização & Sistema"])
def root_info() -> Dict[str, Any]:
    """Retorna informações do sistema e ligações diretas para a documentação Swagger."""
    return {
        "sistema": "Agricultural Decision Support System - Planalto Central de Angola",
        "versao": "1.0.0",
        "regiao": "Planalto Central (Huambo, Bié, Huíla)",
        "documentacao_swagger": "/docs",
        "documentacao_redoc": "/redoc",
        "especificacao_openapi": "/openapi.json",
        "endpoints_principais": {
            "advisory": "/api/v1/advisory",
            "evaluate": "/api/v1/evaluate",
            "provinces": "/api/v1/provinces",
            "baseline": "/api/v1/baseline/{provincia}",
            "health": "/health",
        },
    }


@app.get("/swagger", include_in_schema=False)
def swagger_redirect():
    """Atalho conveniente para o Swagger UI."""
    return RedirectResponse(url="/docs")


@app.get("/api/v1/info", tags=["Monitorização & Sistema"])
def api_info() -> Dict[str, Any]:
    """Retorna metadados operacionais e resumo das capacidades da API."""
    return {
        "sistema": "Agricultural Decision Support System - Planalto Central de Angola",
        "versao": "1.0.0",
        "regiao": "Planalto Central (Huambo, Bié, Huíla)",
        "culturas_suportadas": list(CROPS.keys()),
        "documentacao_swagger": "/docs",
        "documentacao_redoc": "/redoc",
        "especificacao_openapi": "/openapi.json",
        "endpoints": {
            "advisory": "POST /api/v1/advisory",
            "evaluate": "POST /api/v1/evaluate",
            "provinces": "GET /api/v1/provinces",
            "baseline": "GET /api/v1/baseline/{provincia}",
            "health": "GET /health",
        },
    }


@app.get("/health", tags=["Monitorização & Sistema"])
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


@app.get("/api/v1/provinces", response_model=List[ProvinceInfo], tags=["Províncias & Agroecologia"])
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


@app.get("/api/v1/baseline/{provincia}", tags=["Linha de Base NASA POWER"])
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


# Predefined interactive examples for Swagger UI
ADVISORY_EXAMPLES = {
    "exemplo_1_huambo_atual": {
        "summary": "1. Huambo - Milho (Data de Hoje)",
        "description": "O agricultor seleciona Huambo para milho. A data é assumida automaticamente pelo sistema.",
        "value": {
            "provincia": "Huambo",
            "cultura": "Milho"
        }
    },
    "exemplo_2_bie_feijao": {
        "summary": "2. Bié - Feijão (Data de Hoje)",
        "description": "Consulta para feijão na província do Bié com limiares específicos para leguminosas.",
        "value": {
            "provincia": "Bié",
            "cultura": "Feijão"
        }
    },
    "exemplo_3_huila_data": {
        "summary": "3. Huíla - Milho (Data Específica)",
        "description": "Consulta na Huíla especificando uma data de planeamento no pico de Novembro.",
        "value": {
            "provincia": "Huíla",
            "cultura": "Milho",
            "data_consulta": "2026-11-12"
        }
    },
    "exemplo_4_epoca_seca": {
        "summary": "4. Huambo - Teste de Época Seca (Julho)",
        "description": "Simulação de consulta durante a estiagem (Julho) para validação do alerta de Não Plantar.",
        "value": {
            "provincia": "Huambo",
            "cultura": "Milho",
            "data_consulta": "2026-07-15"
        }
    }
}


@app.post("/api/v1/evaluate", response_model=DecisionEvaluationResult, tags=["Decisão Heurística"])
def evaluate_decision_only(
    payload: AdvisoryRequest = Body(..., openapi_examples=ADVISORY_EXAMPLES)
) -> DecisionEvaluationResult:
    """Executa a avaliação agronómica determinística das regras heurísticas sem síntese LLM."""
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


@app.post("/api/v1/advisory", response_model=AdvisoryResponse, tags=["Recomendação & RAG"])
def get_agricultural_advisory(
    payload: AdvisoryRequest = Body(..., openapi_examples=ADVISORY_EXAMPLES)
) -> AdvisoryResponse:
    """Endpoint Principal: Avalia o período de sementeira e devolve a recomendação formal via RAG."""
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
