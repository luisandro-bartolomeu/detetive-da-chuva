# 📱 Guia de Integração Frontend & Design System (UX/UI)
### Sistema de Suporte à Decisão Agrícola - Planalto Central de Angola

Este documento serve como contrato de interface e guia prático para a equipa de **Frontend (Web/Mobile)** consumir a API e construir uma experiência de utilizador (UX) intuitiva, acessível e otimizada para agricultores familiares e extensionistas rurais no terreno.

---

## 1. Endereços da API e Swagger de Produção

| Recurso | URL | Descrição |
|---|---|---|
| **Swagger UI Interativo** | `GET /docs` | Teste interativo com cenários predefinidos |
| **ReDoc** | `GET /redoc` | Documentação técnica visual |
| **Especificação OpenAPI** | `GET /openapi.json` | JSON OpenAPI v3 para geradores automáticos de código |
| **Healthcheck** | `GET /health` | Monitorização de status do serviço |

---

## 2. Mapa dos Endpoints para a Interface

### 🟢 Fluxo Recomendado para o Ecrã:
```
[1. Carregar Ecrã] ────────► GET /api/v1/provinces  (Preenche dropdown de Províncias)
                   ────────► GET /api/v1/crops      (Preenche dropdown de Culturas)
                                   │
[2. Ação do Agricultor]            ▼
Escolhe Província + Cultura ──► POST /api/v1/advisory
                                   │
[3. Renderização do Ecrã]          ▼
Apresenta Card de Veredito + Score de Confiança + Grelha de Métricas + Recomendação
```

---

## 3. Interfaces TypeScript (Copiar para `src/types/advisory.ts`)

```typescript
export type AdvisoryStatus = 'FAVORAVEL' | 'AGUARDAR' | 'DESFAVORAVEL';
export type UrgencyLevel = 'sucesso' | 'atencao' | 'alerta';

export interface UIHints {
  cor_status_hex: string;      // ex: "#16A34A", "#D97706", "#DC2626"
  rotulo_status: string;       // ex: "Favorável para Semear", "Aguardar Consolidação"
  icone: string;               // ex: "✅", "⏳", "⛔"
  nivel_urgencia: UrgencyLevel;
}

export interface AdvisoryMetrics {
  chuva_acumulada_recente_mm: number;  // Chuva dos últimos 3-5 dias (mm)
  humidade_solo_raiz: number;          // Fração 0 a 1
  previsao_7dias_mm: number;           // Previsão para a próxima semana (mm)
  humidade_solo_superficie?: number;   // Fração 0 a 1 (0-7 cm)
  temperatura_max_prevista_c?: number; // Temperatura máxima prevista (°C)
  p25_historico_raiz?: number;         // Limiar mínimo histórico de sobrevivência
  probabilidade_sementeira_semanal?: number; // Probabilidade histórica (%)
}

export interface AdvisoryRequest {
  provincia: 'Huambo' | 'Bié' | 'Huíla' | string;
  cultura?: 'Milho' | 'Feijão' | 'Soja' | string;
  data_consulta?: string; // Opcional (YYYY-MM-DD). Assume hoje se omitida.
}

export interface AdvisoryResponse {
  status: AdvisoryStatus;
  score_confianca: number; // 0 a 100
  metricas: AdvisoryMetrics;
  recomendacao_extensao: string; // Markdown formal e formatado
  ui_hints?: UIHints;
}

export interface ProvinceInfo {
  id: string;
  nome: string;
  latitude: number;
  longitude: number;
  altitude_m: number;
  zona_agroecologica: string;
  icone: string;
}

export interface CropInfo {
  id: string;
  nome: string;
  nome_cientifico: string;
  icone: string;
  profundidade_sementeira_cm: number;
  min_chuva_abertura_mm: number;
  notas_agronomicas: string;
}
```

---

## 4. Design System & Diretrizes de UX

### A. Cores e Badges de Veredito (Paleta Tailwind / CSS)

| Status | Cor HEX | Cor de Fundo (Badge) | Cor de Borda | Ícone | Rótulo Recomendado |
|---|---|---|---|---|---|
| **`FAVORAVEL`** | `#16A34A` (green-600) | `#DCFCE7` (green-100) | `#86EFAC` (green-300) | ✅ | **Favorável para Semear** |
| **`AGUARDAR`** | `#D97706` (amber-600) | `#FEF3C7` (amber-100) | `#FCD34D` (amber-300) | ⏳ | **Aguardar Consolidação** |
| **`DESFAVORAVEL`** | `#DC2626` (red-600) | `#FEE2E2` (red-100) | `#FCA5A5` (red-300) | ⛔ | **Não Plantar Agora** |

> **Nota:** A API já devolve o campo `ui_hints.cor_status_hex` e `ui_hints.rotulo_status`, permitindo que o frontend aplique a cor e o rótulo diretamente sem lógica duplicada!

---

### B. Cartões de Métricas no Dashboard

Recomenda-se dispor as 3 métricas principais em **3 cartões de destaque**:

1. **🌧️ Chuva Recente (3-5 dias):**
   * Valor: `metricas.chuva_acumulada_recente_mm` + `" mm"`
   * Subtítulo: *Chuva já infiltrada no solo*
   * Dica visual: Destacar a verde se $\ge 20\text{ mm}$.

2. **💧 Reserva da Raiz:**
   * Valor: `(metricas.humidade_solo_raiz * 100).toFixed(0)` + `"%" de saturação`
   * Subtítulo: `Limiar mínimo seguro: ${(metricas.p25_historico_raiz * 100).toFixed(0)}%`
   * Dica visual: Barra de nível vertical ou horizontal.

3. **🌤️ Previsão (7 dias):**
   * Valor: `metricas.previsao_7dias_mm` + `" mm previstos"`
   * Subtítulo: `Máx: ${metricas.temperatura_max_prevista_c}°C`
   * Dica visual: Alerta de sol se chuva $< 2\text{ mm}$ e temperatura $> 32^\circ\text{C}$.

---

### C. Barra / Indicador de Confiança (`score_confianca`)
* Valor de `0` a `100%`.
* Sugestão visual: Barra de progresso horizontal ou anel circular (Radial Progress) ao lado do Veredito:
  * `85% a 100%`: Verde (Alta confiança agroclimática)
  * `70% a 84%`: Azul / Âmbar (Confiança sólida)
  * `< 70%`: Amarelo (Condições limítrofes)

---

### D. Renderização da Recomendação (`recomendacao_extensao`)
* O texto devolvido pelo backend utiliza **Markdown estruturado**.
* Utilize um componente como `react-markdown`, `vue-markdown` ou similar com estilo de tipografia (`prose` do Tailwind).
* A primeira linha sempre destaca o **Veredito em negrito**.
* As justificações vêm em lista numerada ou tópicos diretos.
* A seção final contém a **Recomendação Prática de Campo** (teste do torrão de terra a 5 cm), ideal para colocar dentro de uma caixa com borda destacada estilo *"Dica do Agrónomo"*.

---

## 5. Exemplo de Hook React / TypeScript (`useAgroAdvisory.ts`)

```typescript
import { useState, useEffect } from 'react';
import axios from 'axios';
import { AdvisoryResponse, ProvinceInfo, CropInfo } from './types/advisory';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function useAgroAdvisory() {
  const [provinces, setProvinces] = useState<ProvinceInfo[]>([]);
  const [crops, setCrops] = useState<CropInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AdvisoryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // 1. Carregar listas de províncias e culturas ao iniciar
  useEffect(() => {
    async function fetchMetadata() {
      try {
        const [provRes, cropsRes] = await Promise.all([
          axios.get<ProvinceInfo[]>(`${API_BASE_URL}/api/v1/provinces`),
          axios.get<CropInfo[]>(`${API_BASE_URL}/api/v1/crops`),
        ]);
        setProvinces(provRes.data);
        setCrops(cropsRes.data);
      } catch (err) {
        console.error('Erro ao carregar metadados da API:', err);
      }
    }
    fetchMetadata();
  }, []);

  // 2. Função de consulta
  async function consultarSementeira(provincia: string, cultura: string = 'Milho') {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.post<AdvisoryResponse>(
        `${API_BASE_URL}/api/v1/advisory`,
        { provincia, cultura }
      );
      setResult(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao consultar a API.');
    } finally {
      setLoading(false);
    }
  }

  return {
    provinces,
    crops,
    loading,
    result,
    error,
    consultarSementeira,
  };
}
```

---

## 6. Como Hospedar a API em PaaS Gratuito

A API inclui todos os ficheiros de deploy necessários:
* **`render.yaml`** (Render.com - 1-Click Blueprint)
* **`Procfile`** (Railway / Render / Heroku)
* **`Dockerfile`** (Fly.io / Koyeb / Hugging Face Spaces / Qualquer container)

### Opção 1: Render.com (Recomendado - Free Tier)
1. Crie uma conta gratuita em [render.com](https://render.com).
2. Clique em **New +** -> **Web Service** -> Conecte o repositório GitHub do projeto.
3. Configure:
   * **Runtime:** `Python 3`
   * **Build Command:** `pip install -r requirements.txt`
   * **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Na aba **Environment Variables**, adicione:
   * `GEMINI_API_KEY`: *(A sua chave do Google Gemini)*
   * `LLM_MODEL`: `gemini-3.5-flash`
   * `LLM_PROVIDER`: `gemini`
5. Clique em **Create Web Service**. Em 2 a 3 minutos a API estará online com HTTPS gratuito e Swagger ativo em `https://seu-app.onrender.com/docs`.

### Opção 2: Railway.app / Koyeb (Docker)
1. Conecte o repositório.
2. O Railway ou Koyeb detectará automaticamente o `Dockerfile` incluído.
3. Defina a variável de ambiente `GEMINI_API_KEY`.
4. O deploy é executado automaticamente.
