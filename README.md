# 🌽 Sistema de Suporte à Decisão Agrícola (Backend & RAG Pipeline)
### Planalto Central de Angola (Huambo, Bié e Huíla)

Backend analítico e pipeline RAG (Retrieval-Augmented Generation) desenvolvido para apoiar agricultores familiares e extensionistas rurais no Planalto Central de Angola a determinar o momento ideal para a sementeira de culturas alimentares (**milho**, **feijão** e **soja**).

O sistema cruza **25 anos de observações diárias de satélite da NASA POWER (2000–2024)** com dados meteorológicos e previsões em tempo real da **Open-Meteo**, aplicando regras agroclimáticas determinísticas e sintetizando orientações formais, simples e sem jargões através do **Google Gemini**.

---

## 📑 Índice
1. [Guia de Endpoints para a Equipa de Frontend](#1-guia-de-endpoints-para-a-equipa-de-frontend)
   - [`POST /api/v1/advisory` (Endpoint Principal de Recomendação)](#a-post-apiv1advisory)
   - [`GET /api/v1/provinces` (Listar Províncias para Dropdown)](#b-get-apiv1provinces)
   - [`GET /api/v1/crops` (Listar Culturas para Dropdown)](#c-get-apiv1crops)
   - [`POST /api/v1/evaluate` (Avaliação Heurística sem LLM)](#d-post-apiv1evaluate)
   - [`GET /api/v1/baseline/{provincia}` (Linha de Base NASA 2000-2024)](#e-get-apiv1baselineprovincia)
   - [`GET /health` (Verificação de Saúde)](#f-get-health)
   - [`GET /` (Informações do Sistema)](#g-get-)
2. [Orientações de UI/UX para o Frontend](#2-orientações-de-uiux-para-o-frontend)
3. [Segurança em Produção: Desativação do Swagger](#3-segurança-em-produção-desativação-do-swagger)
4. [Como Hospedar em PaaS Gratuito (Render, Railway, Koyeb)](#4-como-hospedar-em-paas-gratuito)
5. [Execução e Testes Locais](#5-execução-e-testes-locais)

---

## 1. Guia de Endpoints para a Equipa de Frontend

Todos os endpoints operam sobre `JSON`, suportam CORS irrestrito (`*`) e não exigem autenticação prévia nesta versão.

---

### A. `POST /api/v1/advisory`
> **Principal:** É o endpoint central consumido pela aplicação quando o agricultor submete a consulta.

#### 📥 Requisição:
* **Método:** `POST`
* **URL:** `/api/v1/advisory`
* **Cabeçalho:** `Content-Type: application/json`

##### Corpo da Requisição (Campos):
| Campo | Tipo | Obrigatório | Descrição | Valor por Omissão |
|---|---|---|---|---|
| `provincia` | `string` | **Sim** | Província selecionada: `"Huambo"`, `"Bié"` ou `"Huíla"` (aceita sem acentos: `"Bie"`, `"Huila"`). | — |
| `cultura` | `string` | Não | Cultura agrícola visada: `"Milho"`, `"Feijão"` ou `"Soja"`. | `"Milho"` |
| `data_consulta` | `string` | Não | Data no formato `YYYY-MM-DD`. Se omitida, o backend assume a data de hoje. | Data atual do sistema |

##### Exemplo de Requisição Mínima (Apenas escolhendo a província):
```json
{
  "provincia": "Huambo"
}
```

##### Exemplo de Requisição Completa:
```json
{
  "provincia": "Huambo",
  "cultura": "Milho",
  "data_consulta": "2026-11-12"
}
```

---

#### 📤 Resposta:
* **Código de Sucesso:** `200 OK`
* **Formato:**
```json
{
  "status": "AGUARDAR",
  "score_confianca": 82,
  "metricas": {
    "chuva_acumulada_recente_mm": 48.2,
    "humidade_solo_raiz": 0.341,
    "previsao_7dias_mm": 83.4
  },
  "recomendacao_extensao": "**AGUARDAR: Recomenda-se aguardar antes de realizar a sementeira de Milho na província do Huambo.**\n\n### Justificações Objetivas:\n* **Reservas hídricas no solo:** A camada superficial do terreno já apresenta uma humidade satisfatória, porém a humidade em profundidade, na zona de desenvolvimento das raízes, ainda está em processo de recarga...\n\n### Recomendação Prática de Campo:\n1. Aproveite os próximos 2 a 3 dias para concluir a preparação da terra...\n2. Faça o teste do torrão na palma da mão a 5 cm de profundidade..."
}
```

##### Descrição dos Campos da Resposta:
* **`status`** (`string`): Veredito agronómico determinístico. Tem apenas 3 valores possíveis:
  * `"FAVORAVEL"`: Condições favoráveis. O agricultor pode semear.
  * `"AGUARDAR"`: Chuvas recentes insuficientes ou solo ainda em recarga. O agricultor deve preparar o terreno e esperar.
  * `"DESFAVORAVEL"`: Período de seca ou estiagem aguda. Não semear para não perder as sementes.
* **`score_confianca`** (`number` de 0 a 100): Grau de certeza agronómica baseado na convergência dos indicadores meteorológicos e na estabilidade histórica do mês.
* **`metricas`** (`object`):
  * **`chuva_acumulada_recente_mm`** (`number`): Volume de chuva registado nos últimos 3 a 5 dias (em mm).
  * **`humidade_solo_raiz`** (`number` de 0.00 a 1.00): Nível de humidade na zona radicular (ex: `0.341` = 34.1%).
  * **`previsao_7dias_mm`** (`number`): Volume total de chuva previsto para a próxima semana (em mm).
* **`recomendacao_extensao`** (`string`): Texto formal em **Markdown** redigido para orientação direta do agricultor. Inclui veredito em destaque, 2 a 3 justificações e a dica prática de campo (teste do torrão).

---

### B. `GET /api/v1/provinces`
> Devolve a lista de províncias suportadas para preenchimento dinâmico de dropdowns no frontend.

* **Método:** `GET`
* **URL:** `/api/v1/provinces`
* **Resposta (`200 OK`):**
```json
[
  {
    "id": "huambo",
    "nome": "Huambo",
    "latitude": -12.7761,
    "longitude": 15.7392,
    "altitude_m": 1700,
    "zona_agroecologica": "Planalto Central Tropical de Altitude"
  },
  {
    "id": "bie",
    "nome": "Bié",
    "latitude": -12.3833,
    "longitude": 16.9333,
    "altitude_m": 1650,
    "zona_agroecologica": "Planalto Central Oriental"
  },
  {
    "id": "huila",
    "nome": "Huíla",
    "latitude": -14.9172,
    "longitude": 13.5414,
    "altitude_m": 1760,
    "zona_agroecologica": "Planalto de Humpata e Lubango"
  }
]
```

---

### C. `GET /api/v1/crops`
> Devolve as culturas agrícolas disponíveis no sistema com metadados para seletores.

* **Método:** `GET`
* **URL:** `/api/v1/crops`
* **Resposta (`200 OK`):**
```json
[
  {
    "id": "milho",
    "nome": "Milho",
    "nome_cientifico": "Zea mays",
    "icone": "🌽",
    "profundidade_sementeira_cm": 5,
    "min_chuva_abertura_mm": 20.0,
    "notas_agronomicas": "Cultura base de segurança alimentar no Planalto Central. Exige solo húmido até 5 cm."
  },
  {
    "id": "feijao",
    "nome": "Feijão",
    "nome_cientifico": "Phaseolus vulgaris",
    "icone": "🫘",
    "profundidade_sementeira_cm": 4,
    "min_chuva_abertura_mm": 18.0,
    "notas_agronomicas": "Muito sensível ao encharcamento prolongado e a veranicos pós-germinação."
  },
  {
    "id": "soja",
    "nome": "Soja",
    "nome_cientifico": "Glycine max",
    "icone": "🌱",
    "profundidade_sementeira_cm": 4,
    "min_chuva_abertura_mm": 22.0,
    "notas_agronomicas": "Exige humidade contínua na sementeira para boa taxa de emergência."
  }
]
```

---

### D. `POST /api/v1/evaluate`
> Avaliação agronómica determinística das regras heurísticas **sem chamada a LLM**. Útil para modo rápido, testes offline ou interfaces de diagnóstico.

* **Método:** `POST`
* **URL:** `/api/v1/evaluate`
* **Corpo:** O mesmo payload de `AdvisoryRequest` (`provincia`, `cultura`, `data_consulta`).
* **Resposta (`200 OK`):**
```json
{
  "status": "AGUARDAR",
  "score_confianca": 82,
  "triggers_ativados": [
    "CRITICAL_ROOT_MOISTURE_DEFICIT",
    "RECENT_RAIN_TRIGGER_SATISFIED"
  ],
  "justificacoes_tecnicas": [
    "Humidade da raiz (0.34) ainda está em recarga. Chuvas fortes previstas (27.1 mm) devem ensopar o terreno em breve.",
    "Recomenda-se preparar as covas e aguardar 2 a 3 dias para a água infiltrar adequadamente."
  ],
  "metricas": {
    "chuva_acumulada_recente_mm": 48.2,
    "humidade_solo_raiz": 0.341,
    "previsao_7dias_mm": 83.4
  },
  "is_fallback_weather": false
}
```

---

### E. `GET /api/v1/baseline/{provincia}`
> Retorna a linha de base histórica completa de 25 anos da NASA POWER para a província solicitada (médias mensais, percentis de humidade P25/P50/P75, curvas semanais 1-52 e teste de Mann-Kendall).

* **Método:** `GET`
* **URL:** `/api/v1/baseline/Huambo` *(ou `Bié` / `Huíla`)*
* **Resposta (`200 OK`):**
```json
{
  "id": "huambo",
  "nome": "Huambo",
  "coordenadas": {
    "latitude": -12.7761,
    "longitude": 15.7392,
    "altitude_m": 1700
  },
  "zona_agroecologica": "Planalto Central Tropical de Altitude",
  "linha_base_mensal": {
    "11": {
      "month": 11,
      "chuva_media_mensal_mm": 219.5,
      "probabilidade_dia_chuvoso_pct": 46.1,
      "gwetroot_p25": 0.432,
      "gwetroot_p50": 0.48,
      "gwetroot_p75": 0.54,
      "temperatura_media_c": 20.5
    }
  },
  "curva_sementeira_semanal": {
    "45": {
      "week": 45,
      "probabilidade_sementeira_pct": 72.0,
      "gwetroot_mediana": 0.47
    }
  },
  "analise_tendencias_mann_kendall": {
    "precipitacao_anual": { "tendencia": "no trend", "p_valor": 0.27234 },
    "temperatura_media_anual": { "tendencia": "no trend", "p_valor": 0.29327 }
  }
}
```

---

### F. `GET /health`
> Healthcheck do serviço e verificação de prontidão da base de dados.

* **Método:** `GET`
* **URL:** `/health`
* **Resposta (`200 OK`):**
```json
{
  "status": "healthy",
  "baseline_ready": true,
  "provincias_ativas": ["Huambo", "Bié", "Huíla"],
  "culturas_ativas": ["Milho", "Feijão", "Soja"],
  "data_servidor": "2026-11-12"
}
```

---

### G. `GET /`
> Informações operacionais e verificação do ambiente (produção vs. desenvolvimento).

* **Método:** `GET`
* **URL:** `/`
* **Resposta (`200 OK`):**
```json
{
  "sistema": "Agricultural Decision Support System - Planalto Central de Angola",
  "versao": "1.0.0",
  "regiao": "Planalto Central (Huambo, Bié, Huíla)",
  "ambiente": "production",
  "swagger_disponivel": false
}
```

---

## 2. Orientações de UI/UX para o Frontend

A equipa de frontend pode estruturar o ecrã com base nas seguintes convenções:

### A. Cores e Badges de Veredito (`status`)
| Valor de `status` | Cor de Destaque | Sugestão de Badge | Ícone Visual | Ação Sugerida ao Agricultor |
|---|---|---|---|---|
| **`FAVORAVEL`** | Verde (`#16A34A`) | Fundo `#DCFCE7`, Texto `#15803D` | ✅ | Indicar que o solo tem reserva hídrica e pode semear. |
| **`AGUARDAR`** | Âmbar/Amarelo (`#D97706`) | Fundo `#FEF3C7`, Texto `#B45309` | ⏳ | Orientar a preparar o terreno e esperar que a terra beba mais água. |
| **`DESFAVORAVEL`** | Vermelho (`#DC2626`) | Fundo `#FEE2E2`, Texto `#B91C1C` | ⛔ | Alertar para guardar as sementes para não perdê-las na seca. |

### B. Confiança da Recomendação (`score_confianca`)
* Exibir como uma **barra de progresso** ou **indicador circular** (0 a 100%).
* Exemplo: `82% de Certeza Agroclimática`.

### C. Apresentação das Métricas (`metricas`)
Recomenda-se renderizar em **3 cartões horizontais ou grelha de 3 colunas**:
1. **🌧️ Chuva Recente:** `metricas.chuva_acumulada_recente_mm` + `" mm"` *(Últimos 3-5 dias)*.
2. **💧 Humidade da Raiz:** `(metricas.humidade_solo_raiz * 100).toFixed(0)` + `"%"` *(Água guardada no solo)*.
3. **🌤️ Previsão (7 dias):** `metricas.previsao_7dias_mm` + `" mm"` *(Chuva prevista)*.

### D. Recomendação Escrita (`recomendacao_extensao`)
* O campo contém texto formatado em **Markdown**.
* Utilize um parser como `react-markdown` para renderizar negritos, parágrafos e listas com boa tipografia legível em ecrãs móveis sob luz solar no campo.

---

## 3. Segurança em Produção: Desativação do Swagger

Por boas práticas de segurança, **em ambiente de produção não é permitido aceder ao Swagger UI (`/docs`), ReDoc (`/redoc`) ou à especificação aberta (`/openapi.json`)**.

### Como Funciona:
A API lê a variável de ambiente `ENVIRONMENT`:
* Se `ENVIRONMENT=production`:
  * `/docs` $\rightarrow$ **`404 Not Found`**
  * `/redoc` $\rightarrow$ **`404 Not Found`**
  * `/openapi.json` $\rightarrow$ **`404 Not Found`**
* Se `ENVIRONMENT=development` (ou local):
  * `/docs` $\rightarrow$ Ativo para testes e depuração de desenvolvimento.

---

## 4. Como Hospedar em PaaS Gratuito

O repositório inclui todos os ficheiros de configuração de deploy prontos:
* **`render.yaml`** (Render.com)
* **`Procfile`** (Railway / Heroku / Render)
* **`Dockerfile`** (Fly.io / Koyeb / Hugging Face Spaces)

### Deploy no Render.com (Web Service Gratuito):
1. Faça push do código para o seu repositório no **GitHub**.
2. No painel do [Render](https://render.com), clique em **New +** $\rightarrow$ **Web Service**.
3. Conecte o repositório GitHub.
4. Preencha as configurações:
   * **Runtime:** `Python 3`
   * **Build Command:** `pip install -r requirements.txt && python -c "from src.baseline_engine import BaselineEngine; BaselineEngine().load_baseline()"`
   * **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Na secção **Environment Variables**, adicione:
   * `ENVIRONMENT`: `production` *(desativa o Swagger automaticamente)*
   * `GEMINI_API_KEY`: *(A sua chave do Google Gemini)*
   * `LLM_MODEL`: `gemini-3.5-flash`
   * `LLM_PROVIDER`: `gemini`
6. Clique em **Create Web Service**. Em cerca de 2 minutos a API estará no ar com HTTPS gratuito.

---

## 5. Execução e Testes Locais

### 1. Iniciar o Servidor Localmente:
```bash
python run_pipeline.py
```
*(O script valida automaticamente os 3 ficheiros JSON da NASA, verifica a linha de base e inicia o servidor FastAPI na porta 8000).*

### 2. Executar a Suíte de Testes Automatizados:
```bash
pytest -v
```
*(Todos os 22 testes unitários e de integração cobrem a ingestão, os percentis, as heurísticas, o Gemini e a desativação de segurança do Swagger em produção).*
