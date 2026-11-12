# Agricultural Decision Support System (Backend & RAG Pipeline)
### Sistema de Suporte à Decisão Agrícola para o Planalto Central de Angola (Huambo, Bié e Huíla)

Sistema de avaliação agroclimática determinística e geração aumentada por recuperação (RAG) para apoiar camponeses e pequenos produtores familiares na determinação da época ideal de sementeira (milho, feijão e soja).

---

## 1. Visão Geral da Arquitetura

O sistema articula quatro camadas técnicas essenciais:

```
┌─────────────────────────────────┐       ┌─────────────────────────────────┐
│     Dados Históricos 25 Anos    │       │     Previsão em Tempo Real      │
│      NASA POWER (2000-2024)     │       │       API Open-Meteo            │
│  (Chuva, GWETROOT, GWETTOP, T)  │       │   (7d passado + 7d futuro)      │
└────────────────┬────────────────┘       └────────────────┬────────────────┘
                 │                                         │
                 ▼                                         ▼
   ┌───────────────────────────┐             ┌───────────────────────────┐
   │ Module 1: baseline_engine │             │ Module 2: weather_service │
   │ (Percentis P25/P50/P75,   │             │ (Chuva recente, 48h, 7d,  │
   │  Curvas Semanals, M-K)    │             │  Humidade raiz & fallback)│
   └─────────────┬─────────────┘             └─────────────┬─────────────┘
                 │                                         │
                 └───────────────────┬─────────────────────┘
                                     ▼
                      ┌─────────────────────────────┐
                      │  Module 3: decision_engine  │
                      │  (Critérios Heurísticos:    │
                      │   - CRITICAL_ROOT_MOISTURE  │
                      │   - RECENT_RAIN_TRIGGER     │
                      │   - DRY_SPELL_RISK          │
                      │   Veredito + Confiança 0-100)│
                      └──────────────┬──────────────┘
                                     ▼
                      ┌─────────────────────────────┐
                      │    Module 4: rag_service    │
                      │  (Context Chunking + LLM    │
                      │   Extensionista Angolano)   │
                      └──────────────┬──────────────┘
                                     ▼
                      ┌─────────────────────────────┐
                      │     Module 5: main.py       │
                      │    FastAPI HTTP Endpoint    │
                      │   POST /api/v1/advisory     │
                      └─────────────────────────────┘
```

---

## 2. Estrutura do Projeto

```
.
├── data/
│   ├── nasa_power_raw_huambo_2000_2024.json   # 9.132 dias diários
│   ├── nasa_power_raw_bie_2000_2024.json      # 9.132 dias diários
│   ├── nasa_power_raw_huila_2000_2024.json    # 9.132 dias diários
│   └── processed_baseline.json                # Matrizes consolidadas geradas
├── src/
│   ├── __init__.py
│   ├── config.py             # Configurações, coordenadas e limiares
│   ├── schemas.py            # Modelos Pydantic v2
│   ├── baseline_engine.py    # Módulo 1: Ingestão, estatísticas e Mann-Kendall
│   ├── weather_service.py    # Módulo 2: Integração Open-Meteo e fallback
│   ├── decision_engine.py    # Módulo 3: Motor de regras heurísticas
│   └── rag_service.py        # Módulo 4: Chunking de contexto e síntese RAG
├── tests/
│   ├── test_baseline.py      # Testes de linha de base e tendências
│   ├── test_weather.py       # Testes da meteorologia e resiliência
│   ├── test_decision.py      # Testes de gatilhos e pontuação
│   └── test_api.py           # Testes dos endpoints FastAPI
├── main.py                   # Módulo 5: Aplicação FastAPI
├── run_pipeline.py           # Ponto de entrada CLI único
├── requirements.txt          # Dependências do projeto
├── .env.example              # Exemplo de variáveis de ambiente
└── README.md
```

---

## 3. Instalação e Execução

### Pré-requisitos
- Python 3.10+
- Dependências instaladas:
  ```bash
  pip install -r requirements.txt
  ```

### Ponto de Entrada Único (`run_pipeline.py`)
O script verifica a existência dos 3 ficheiros brutos da NASA POWER, processa a linha de base se necessário e inicia o servidor FastAPI:
```bash
python run_pipeline.py
```

Opções adicionais:
- `--no-server`: Apenas valida dados e processa a linha de base.
- `--recompute-baseline`: Força o recálculo das matrizes agroclimáticas.
- `--host 0.0.0.0 --port 8000`: Especifica porta e endereço de rede.

---

## 4. Endpoints da API

### `POST /api/v1/advisory` (Endpoint Principal)
Gera o veredito agronómico, métricas consolidadas e o texto de extensão rural sintetizado por RAG.

#### Exemplo de Requisição:
```json
{
  "provincia": "Huambo",
  "cultura": "Milho",
  "data_consulta": "2026-11-12"
}
```

#### Exemplo de Resposta:
```json
{
  "status": "AGUARDAR",
  "score_confianca": 82,
  "metricas": {
    "chuva_acumulada_recente_mm": 48.2,
    "humidade_solo_raiz": 0.341,
    "previsao_7dias_mm": 83.4
  },
  "recomendacao_extensao": "**AGUARDAR: Tenha calma, meu irmão camponês; ainda não é a melhor hora para deitar a semente à terra no Huambo.**\n\nA terra está a começar a despertar, mas ainda requer cautela para não perdermos o trabalho nem as sementes:\n\n1. **Chão ainda a recarregar:** Embora já tenha caído alguma chuva (48.2 mm), a reserva de água mais abaixo onde a raiz vai crescer ainda está rasa..."
}
```

### Outros Endpoints:
- `GET /`: Informações e estado da API.
- `GET /health`: Healthcheck e verificação da prontidão dos dados.
- `GET /api/v1/provinces`: Lista das províncias suportadas (Huambo, Bié, Huíla).
- `GET /api/v1/baseline/{provincia}`: Matrizes agroclimáticas mensais, semanais e testes de Mann-Kendall.
- `POST /api/v1/evaluate`: Avaliação determinística pura sem chamada a LLM.

---

## 5. Testes Automatizados

O projeto inclui um conjunto completo de 19 testes automatizados com `pytest`:
```bash
pytest -v
```
Todos os testes cobrem ingestão, percentis de linha de base, curvas semanais, Mann-Kendall, resiliência do Open-Meteo, regras heurísticas e validação estrita dos schemas Pydantic v2.
