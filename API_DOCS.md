# Guia de Integração da API - Detetive da Chuva

**URL Base da API:** `https://detetive-da-chuva.onrender.com`  
**Formato de Dados:** `application/json`  
**Autenticação:** Não necessária (Acesso público)  
**CORS:** Habilitado para qualquer origem (`*`)

---

## 1. Listar Províncias Disponíveis

### Para que serve:
Retorna os nomes e identificadores das regiões atendidas pelo sistema.

### Caso de uso:
Carregar dinamicamente a lista ou menu suspenso (dropdown) de províncias para o utilizador escolher antes de fazer a consulta.

### Requisição (Request):
* **Método:** `GET`
* **URL:** `https://detetive-da-chuva.onrender.com/api/v1/provinces`
* **Corpo (Body):** Nenhum

### Resposta (Response):
* **Código:** `200 OK`
* **Exemplo de Resposta:**
```json
[
  {
    "id": "huambo",
    "nome": "Huambo"
  },
  {
    "id": "bie",
    "nome": "Bié"
  },
  {
    "id": "huila",
    "nome": "Huíla"
  }
]
```

### Explicação dos campos:
* `id`: Identificador interno da província.
* `nome`: Nome oficial da província para exibir na interface.

---

## 2. Listar Culturas Agrícolas Disponíveis

### Para que serve:
Retorna as opções de culturas (tipos de plantio) suportadas para análise.

### Caso de uso:
Carregar a lista de opções no formulário de consulta (ex: Milho, Feijão, Soja).

### Requisição (Request):
* **Método:** `GET`
* **URL:** `https://detetive-da-chuva.onrender.com/api/v1/crops`
* **Corpo (Body):** Nenhum

### Resposta (Response):
* **Código:** `200 OK`
* **Exemplo de Resposta:**
```json
[
  {
    "id": "milho",
    "nome": "Milho"
  },
  {
    "id": "feijao",
    "nome": "Feijão"
  },
  {
    "id": "soja",
    "nome": "Soja"
  }
]
```

### Explicação dos campos:
* `id`: Identificador da cultura.
* `nome`: Nome da cultura para exibição no aplicativo.

### Perfis das Culturas Disponíveis:
* **🌽 Milho:** Cultura principal. Exige solo firme e boa humidade contínua. Profundidade ideal de sementeira: 5 cm.
* **🫘 Feijão:** Ciclo mais curto. Suporta menor volume inicial de água, mas é **muito sensível ao excesso de água (encharcamento)**. Se o terreno estiver demasiado molhado, a API recomenda aguardar a drenagem para evitar que a semente apodreça. Profundidade: 3 a 4 cm.
* **🌱 Soja:** Semente que exige elevada absorção de água para germinar. A API só aprova quando as reservas de humidade do solo estão plenamente consolidadas. Profundidade: 3 a 5 cm.

---

## 3. Consultar Orientação Agrícola (Endpoint Principal)

### Para que serve:
Gera a recomendação completa e personalizada sobre a viabilidade da sementeira para a província e cultura indicadas, incluindo o parecer final, o nível de certeza e uma mensagem explicativa com orientações práticas de campo.

### Caso de uso:
Chamado quando o utilizador preenche os dados e clica no botão principal de consulta (ex: *"Verificar Momento de Plantio"*).

### Requisição (Request):
* **Método:** `POST`
* **URL:** `https://detetive-da-chuva.onrender.com/api/v1/advisory`
* **Cabeçalho:** `Content-Type: application/json`

#### Campos do Corpo (Body):
| Campo | Tipo | Obrigatório | Descrição | Valor Padrão se omitido |
|---|---|---|---|---|
| `provincia` | `string` | **Sim** | Nome da província: `"Huambo"`, `"Bié"` ou `"Huíla"`. | — |
| `municipio` | `string` | Não | Nome do município para maior precisão geográfica (ex: `"Caála"`, `"Bailundo"`, `"Kuito"`, `"Matala"`, etc.). | Centro da província |
| `cultura` | `string` | Não | Cultura agrícola visada: `"Milho"`, `"Feijão"` ou `"Soja"`. | `"Milho"` |
| `data_consulta` | `string` | Não | Data da consulta no formato `YYYY-MM-DD` (pode ser a data atual ou qualquer data futura de planeamento de safra, ex: `"2027-11-15"`). | Data de hoje |

#### Exemplo de Requisição (Planeamento Imediato):
```json
{
  "provincia": "Huambo",
  "municipio": "Caála",
  "cultura": "Milho"
}
```

#### Exemplo de Requisição (Planeamento Estratégico Futuro):
```json
{
  "provincia": "Huambo",
  "cultura": "Milho",
  "data_consulta": "2027-11-15"
}
```

### Resposta (Response):
* **Código:** `200 OK`
* **Exemplo de Resposta:**
```json
{
  "status": "AGUARDAR",
  "score_confianca": 82,
  "metricas": {
    "chuva_acumulada_recente_mm": 48.2,
    "humidade_solo_raiz": 0.34,
    "previsao_7dias_mm": 83.4
  },
  "recomendacao_extensao": "**AGUARDAR: Recomenda-se aguardar antes de realizar a sementeira de Milho na província do Huambo.**\n\n### Justificações:\n* **Reservas de água no solo:** Embora o terreno superficial esteja húmido, a água em profundidade ainda está a recuperar...\n\n### Recomendação Prática:\n* Prepare a terra e aguarde as próximas chuvas para que a terra ganhe consistência ideal para a semente."
}
```

### Explicação dos campos da resposta:
* `status` (`string`): Veredito final para a consulta. Pode assumir um destes 3 valores:
  * `"FAVORAVEL"`: Condições propícias. Pode realizar a sementeira.
  * `"AGUARDAR"`: Chuvas insuficientes ou solo ainda a absorver água. Preparar a terra e esperar.
  * `"DESFAVORAVEL"`: Período seco ou desfavorável. Evitar o plantio para não perder sementes.
* `score_confianca` (`number` de 0 a 100): Grau percentual de confiança da recomendação.
* `metricas` (`object`): Indicadores observados para a região:
  * `chuva_acumulada_recente_mm` (`number`): Volume de chuva registado nos últimos dias (em milímetros).
  * `humidade_solo_raiz` (`number` entre 0.0 e 1.0): Nível de humidade na profundidade da raiz (ex: `0.34` equivale a 34%).
  * `previsao_7dias_mm` (`number`): Volume de chuva esperado para os próximos 7 dias (em milímetros).
* `recomendacao_extensao` (`string`): Mensagem de texto formatada com as explicações e o conselho prático ao agricultor.

---

## 4. Avaliação Rápida (Sem Mensagem Extensa)

### Para que serve:
Retorna diretamente o veredito e os números da consulta, sem gerar o texto longo explicativo.

### Caso de uso:
Exibições compactas, painéis de resumo rápido ou consultas em modo económico de dados móveis.

### Requisição (Request):
* **Método:** `POST`
* **URL:** `https://detetive-da-chuva.onrender.com/api/v1/evaluate`
* **Cabeçalho:** `Content-Type: application/json`

#### Exemplo de Requisição:
```json
{
  "provincia": "Bié",
  "cultura": "Feijão"
}
```

### Resposta (Response):
* **Código:** `200 OK`
* **Exemplo de Resposta:**
```json
{
  "status": "AGUARDAR",
  "score_confianca": 85,
  "triggers_ativados": [
    "CRITICAL_ROOT_MOISTURE_DEFICIT",
    "RECENT_RAIN_TRIGGER_SATISFIED"
  ],
  "justificacoes_tecnicas": [
    "Humidade do solo em fase de recarga.",
    "Precipitação prevista favorável nos próximos dias."
  ],
  "metricas": {
    "chuva_acumulada_recente_mm": 35.0,
    "humidade_solo_raiz": 0.32,
    "previsao_7dias_mm": 60.5
  },
  "is_fallback_weather": false
}
```

### Explicação dos campos da resposta:
* `status` (`string`): `"FAVORAVEL"`, `"AGUARDAR"` ou `"DESFAVORAVEL"`.
* `score_confianca` (`number`): Pontuação de 0 a 100.
* `justificacoes_tecnicas` (`array of strings`): Lista de razões objetivas que determinaram a avaliação.
* `metricas` (`object`): Dados de chuva recente, humidade no solo e chuva prevista.

---

## 5. Verificação de Estado da API (Healthcheck)

### Para que serve:
Confirma se o servidor está ativo, operacional e conectado.

### Caso de uso:
Monitoramento de disponibilidade do sistema ou teste inicial de conexão da aplicação móvel/web.

### Requisição (Request):
* **Método:** `GET`
* **URL:** `https://detetive-da-chuva.onrender.com/health`
* **Corpo (Body):** Nenhum

### Resposta (Response):
* **Código:** `200 OK`
* **Exemplo de Resposta:**
```json
{
  "status": "healthy",
  "baseline_ready": true,
  "provincias_ativas": [
    "Huambo",
    "Bié",
    "Huíla"
  ],
  "culturas_ativas": [
    "Milho",
    "Feijão",
    "Soja"
  ],
  "data_servidor": "2026-11-12"
}
```

### Explicação dos campos:
* `status`: `"healthy"` indica que o serviço está operacional.
* `baseline_ready`: `true` confirma que os dados de suporte estão carregados.
* `provincias_ativas`: Lista das províncias prontas para consulta.
* `culturas_ativas`: Lista das culturas configuradas.
* `data_servidor`: Data atual registada no servidor.
