"""Module 5: API Layer.

FastAPI application providing the Agricultural Decision Support System endpoints,
specifically the primary advisory endpoint: POST /api/v1/advisory, with interactive
Swagger UI documentation, rich OpenAPI examples, and UX helpers for frontend teams.
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
    CropInfo,
    UIHints,
    AdvisoryStatus,
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
        "description": "Endpoint principal do sistema para consumo no frontend. "
                       "Avalia as condições hídricas da província escolhida e sintetiza a recomendação técnica formal via Google Gemini.",
    },
    {
        "name": "Seletores de UI (Dropdowns)",
        "description": "Endpoints desenhados especificamente para a equipa de frontend carregar províncias e culturas disponíveis sem hardcoding.",
    },
    {
        "name": "Decisão Heurística (Modo Offline/Auditoria)",
        "description": "Avaliação técnica determinística pura dos gatilhos agroclimáticos sem geração de linguagem natural.",
    },
    {
        "name": "Linha de Base NASA POWER",
        "description": "Consulta às séries históricas pré-computadas (2000-2024), percentis P25/P50/P75, curvas semanais e tendências de Mann-Kendall.",
    },
    {
        "name": "Monitorização & Sistema",
        "description": "Verificação de integridade operacional, ficheiros e conectividade da API.",
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

Bem-vindo à documentação da API do **Sistema de Suporte à Decisão Agrícola** para o **Planalto Central de Angola (Huambo, Bié e Huíla)**.

---

### 🎨 Guia Rápido para a Equipa de Frontend (UX/UI):
1. **Dropdown de Províncias:** Consuma `GET /api/v1/provinces` para preencher o seletor com nome, altitude e zona agroecológica.
2. **Dropdown de Culturas:** Consuma `GET /api/v1/crops` para preencher o seletor com ícones (`🌽`, `🫘`, `🌱`), profundidade e notas agronómicas.
3. **Formulário de Consulta:** Envie `POST /api/v1/advisory` com `{ "provincia": "Huambo", "cultura": "Milho" }`. A data é opcional (o backend assume hoje).
4. **Renderização de Resultados:**
   * A resposta inclui um objeto **`ui_hints`** com `cor_status_hex` (`#16A34A` verde, `#D97706` amarelo, `#DC2626` vermelho), `icone` e `rotulo_status`.
   * Mostre o **`score_confianca`** numa barra de progresso ou indicador visual circular (0–100%).
   * Apresente as métricas fundamentais em cartões visuais (`chuva_acumulada_recente_mm`, `humidade_solo_raiz`, `previsao_7dias_mm`).
   * Renderize o texto **`recomendacao_extensao`** com suporte a Markdown.

---
*Para testar os endpoints agora, selecione um dos cenários predefinidos abaixo e clique em **Execute**.*
""",
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=TAGS_METADATA,
    docs_url="/docs",
    redoc_url="/redoc",
    swagger_ui_parameters=SWAGGER_UI_PARAMETERS,
)

# Enable CORS for frontend applications (React, Vite, Next.js, Flutter, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Monitorização & Sistema"])
def root_info() -> Dict[str, Any]:
    """Retorna metadados operacionais e hiperligações para a documentação Swagger e ReDoc."""
    return {
        "sistema": "Agricultural Decision Support System - Planalto Central de Angola",
        "versao": "1.0.0",
        "regiao": "Planalto Central (Huambo, Bié, Huíla)",
        "documentacao_swagger": "/docs",
        "documentacao_redoc": "/redoc",
        "especificacao_openapi": "/openapi.json",
        "endpoints_principais": {
            "advisory": "POST /api/v1/advisory",
            "provinces": "GET /api/v1/provinces",
            "crops": "GET /api/v1/crops",
            "evaluate": "POST /api/v1/evaluate",
            "baseline": "GET /api/v1/baseline/{provincia}",
            "health": "GET /health",
        },
    }


@app.get("/swagger", include_in_schema=False)
def swagger_redirect():
    """Atalho de redirecionamento conveniente para o Swagger UI (/docs)."""
    return RedirectResponse(url="/docs")


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


@app.get(
    "/api/v1/provinces",
    response_model=List[ProvinceInfo],
    tags=["Seletores de UI (Dropdowns)"],
    summary="Listar Províncias Disponíveis",
    description="Retorna a lista de províncias do Planalto Central com coordenadas, altitude e zonas agroecológicas para preenchimento de dropdowns.",
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
                icone="📍",
            )
        )
    return result


@app.get(
    "/api/v1/crops",
    response_model=List[CropInfo],
    tags=["Seletores de UI (Dropdowns)"],
    summary="Listar Culturas Agrícolas Disponíveis",
    description="Retorna a lista de culturas suportadas com ícones visuais, profundidade recomendada de cova e requisitos hídricos para a UI.",
)
def list_crops() -> List[CropInfo]:
    """Lista as culturas suportadas no sistema para seletores de formulários no frontend."""
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
    tags=["Linha de Base NASA POWER"],
    summary="Consultar Linha de Base Histórica",
    description="Devolve matrizes históricas (2000-2024), médias mensais, percentis radiculares P25/P50/P75, curvas de sementeira e testes de Mann-Kendall.",
)
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


@app.post(
    "/api/v1/evaluate",
    response_model=DecisionEvaluationResult,
    tags=["Decisão Heurística (Modo Offline/Auditoria)"],
    summary="Avaliação Agroclimática Determinística",
    description="Executa o motor de regras heurísticas sem invocar o LLM. Ideal para modo offline, testes de baixa latência e auditoria de gatilhos.",
)
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


@app.post(
    "/api/v1/advisory",
    response_model=AdvisoryResponse,
    tags=["Recomendação & RAG"],
    summary="Obter Recomendação Agroclimática Completa (RAG)",
    description="Endpoint principal consumido pelo frontend. Avalia a aptidão de sementeira e gera o parecer formal com métricas e auxílios visuais (ui_hints).",
    responses={
        200: {
            "description": "Recomendação gerada com sucesso com veredito, score de confiança, métricas e texto formal.",
        },
        400: {
            "description": "Erro de validação (ex: província inválida fora do Planalto Central).",
        },
        422: {
            "description": "Erro nos campos enviados na requisição.",
        },
        500: {
            "description": "Erro interno durante o processamento agroclimático.",
        },
    },
)
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

    # 4. Generate UI Hints for Frontend Engineers
    ui_hints_map = {
        AdvisoryStatus.FAVORAVEL: UIHints(
            cor_status_hex="#16A34A",
            rotulo_status="Favorável para Semear",
            icone="✅",
            nivel_urgencia="sucesso",
        ),
        AdvisoryStatus.AGUARDAR: UIHints(
            cor_status_hex="#D97706",
            rotulo_status="Aguardar Consolidação da Humidade",
            icone="⏳",
            nivel_urgencia="atencao",
        ),
        AdvisoryStatus.DESFAVORAVEL: UIHints(
            cor_status_hex="#DC2626",
            rotulo_status="Não Plantar Agora",
            icone="⛔",
            nivel_urgencia="alerta",
        ),
    }

    ui_hint = ui_hints_map.get(
        eval_result.status,
        UIHints(
            cor_status_hex="#D97706",
            rotulo_status="Aguardar",
            icone="⏳",
            nivel_urgencia="atencao",
        ),
    )

    # 5. Assemble final response conforming strictly to specification
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
        ui_hints=ui_hint,
    )

    return response


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("main:app", host=host, port=port, reload=True)
