"""Module 4: Knowledge Chunking & RAG Synthesis.

Assembles dynamic context blocks from statistical baselines and real-time decision metrics,
prompts LLMs (Gemini / OpenAI) with formal, objective, and culturally grounded agricultural extension instructions,
and provides a resilient deterministic agronomist synthesis fallback.
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Ensure fresh environment variables
load_dotenv()

try:
    from src.schemas import DecisionEvaluationResult, AdvisoryStatus
    from src.config import (
        GEMINI_API_KEY,
        OPENAI_API_KEY,
        LLM_PROVIDER,
        LLM_MODEL,
        PROVINCES,
    )
except ImportError:
    from schemas import DecisionEvaluationResult, AdvisoryStatus
    from config import (
        GEMINI_API_KEY,
        OPENAI_API_KEY,
        LLM_PROVIDER,
        LLM_MODEL,
        PROVINCES,
    )


class RAGService:
    """Manages context assembly, grounding prompts, and LLM text generation."""

    def __init__(self):
        self.gemini_client = None
        self.openai_client = None
        self._init_clients()

    def _init_clients(self):
        """Initializes API clients if keys are present in environment."""
        load_dotenv()
        # Check Gemini
        g_key = os.getenv("GEMINI_API_KEY", GEMINI_API_KEY).strip()
        if g_key:
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=g_key)
            except Exception as e:
                print(f"[!] Aviso ao inicializar Google GenAI: {e}")

        # Check OpenAI
        o_key = os.getenv("OPENAI_API_KEY", OPENAI_API_KEY).strip()
        if o_key:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=o_key)
            except Exception as e:
                print(f"[!] Aviso ao inicializar OpenAI: {e}")

    def build_context_block(
        self,
        provincia: str,
        cultura: str,
        data_consulta: str,
        eval_result: DecisionEvaluationResult,
    ) -> str:
        """Converts statistical baseline and decision engine results into a structured Markdown chunk."""
        details = eval_result.detalhes_agroclimaticos
        m = eval_result.metricas

        # Translate status into agronomic verdict
        status_verdicts = {
            AdvisoryStatus.FAVORAVEL: "FAVORÁVEL (Condições hídricas e térmicas favoráveis para sementeira)",
            AdvisoryStatus.AGUARDAR: "AGUARDAR (Aguardar consolidação das chuvas e reposição da humidade radicular)",
            AdvisoryStatus.DESFAVORAVEL: "NÃO PLANTAR (Desfavorável / Risco elevado de perda de semente por défice hídrico)",
        }
        verdict_str = status_verdicts.get(eval_result.status, "AGUARDAR")

        mes_nome = datetime.strptime(data_consulta, "%Y-%m-%d").strftime("%B") if "-" in data_consulta else "Novembro"
        meses_pt = {
            "January": "Janeiro", "February": "Fevereiro", "March": "Março",
            "April": "Abril", "May": "Maio", "June": "Junho",
            "July": "Julho", "August": "Agosto", "September": "Setembro",
            "October": "Outubro", "November": "Novembro", "December": "Dezembro"
        }
        mes_nome_pt = meses_pt.get(mes_nome, mes_nome)

        context_lines = [
            f"### CONTEXTO AGROCLIMÁTICO REGIONAL - PLANALTO CENTRAL DE ANGOLA",
            f"- **Província Selecionada:** {provincia} (Zona Agroecológica: {PROVINCES.get(provincia, {}).get('agroecological_zone', 'Planalto Central')})",
            f"- **Cultura Agrícola:** {cultura}",
            f"- **Data da Consulta:** {data_consulta} (Mês: {mes_nome_pt}, Semana Agrícola: {details.get('semana_iso', 'N/A')})",
            "",
            f"#### 1. Referência Histórica Agroclimática (NASA POWER 2000-2024)",
            f"- Chuva média histórica do mês: {details.get('chuva_media_mensal_mm', 0):.1f} mm/mês",
            f"- Frequência histórica de condições propícias para a semana: {m.probabilidade_sementeira_semanal or 50:.1f}%",
            f"- Temperatura média típica: {details.get('temperatura_media_c', 20):.1f} °C",
            "",
            f"#### 2. Monitorização Meteorológica Recente e Previsão (Open-Meteo)",
            f"- Chuva acumulada recente (últimos 3 a 5 dias): {m.chuva_acumulada_recente_mm:.1f} mm",
            f"- Previsão de chuva acumulada para os próximos 7 dias: {m.previsao_7dias_mm:.1f} mm",
            f"- Temperatura máxima prevista para os próximos 7 dias: {m.temperatura_max_prevista_c or 26:.1f} °C",
            f"- Humidade atual na zona radicular: {m.humidade_solo_raiz:.3f} (Limiar de segurança hídrica: {m.p25_historico_raiz or 0.40:.3f})",
            f"- Humidade na camada superficial (0-7 cm): {m.humidade_solo_superficie or 0.40:.3f}",
            "",
            f"#### 3. Avaliação Técnica Determinística do Sistema",
            f"- Veredito Oficial: **{verdict_str}**",
            f"- Nível de Confiança da Análise: {eval_result.score_confianca}%",
            f"- Indicadores Ativados: {', '.join(eval_result.triggers_ativados) or 'Condições dentro dos padrões esperados'}",
            f"- Justificações Técnicas:",
        ]

        for just in eval_result.justificacoes_tecnicas:
            context_lines.append(f"  * {just}")

        return "\n".join(context_lines)

    def get_system_prompt(self) -> str:
        """Returns the formal, professional system instructions for the LLM."""
        return (
            "És um Engenheiro Agrónomo e Especialista em Extensão Rural que presta assistência técnica a agricultores "
            "no Planalto Central de Angola (abrangendo Huambo, Bié e Huíla). O teu objetivo é fornecer orientações "
            "técnicas claras, formais, simples e informativas sobre o momento adequado para a sementeira de culturas "
            "como milho, feijão ou soja.\n\n"
            "DIRETRIZES DE ESTILO E CONDUTA:\n"
            "1. TOM FORMAL E PROFISSIONAL: Comunica de forma polida, objetiva, informativa e profissional. "
            "NÃO utilizes tratamentos informais ou coloquiais, tais como 'irmão', 'meu irmão', 'irmão camponês', 'amigo' ou gírias. "
            "A mensagem deve ser respeitosa, sóbria e focada em orientar a tomada de decisão do agricultor.\n"
            "2. ISENÇÃO TOTAL DE JARGÃO TÉCNICO ESTATÍSTICO/COMPUTACIONAL: NUNCA mencione termos como: "
            "'Mann-Kendall', 'SARIMA', 'p-valor', 'P25', 'GWETROOT', 'GWETTOP', 'APIs', 'Open-Meteo', 'NASA POWER', 'percentis', "
            "'algoritmo' ou 'série temporal'. Transmita as conclusões através de termos práticos de solo, chuva, humidade e temperatura.\n"
            "3. ESTRUTURA OBRIGATÓRIA DA RECOMENDAÇÃO:\n"
            "   A) PRIMEIRA LINHA (Veredito explícito em negrito e maiúsculas):\n"
            "      - Caso favorável: '**FAVORÁVEL: O período atual é favorável para a sementeira de [Cultura] na província do [Província].**'\n"
            "      - Caso de espera: '**AGUARDAR: Recomenda-se aguardar antes de realizar a sementeira de [Cultura] na província do [Província].**'\n"
            "      - Caso desfavorável: '**NÃO PLANTAR: O momento atual é desfavorável para a sementeira de [Cultura] na província do [Província].**'\n"
            "   B) JUSTIFICAÇÕES OBJETIVAS (2 a 3 pontos diretos):\n"
            "      - Avaliação das reservas hídricas do solo na zona da raiz.\n"
            "      - Comportamento das chuvas recentes e previsão para os próximos 7 dias.\n"
            "      - Enquadramento agroclimático histórico da época na província.\n"
            "   C) RECOMENDAÇÃO PRÁTICA DE CAMPO:\n"
            "      - Indicação de teste prático simples de terreno (ex.: verificar a humidade na profundidade da semente a cerca de 5 cm, "
            "confirmando a formação de torrão consistente que não esfarela e sem excesso de água).\n\n"
            "Apresenta a resposta em língua portuguesa de Angola, com excelente clareza sintática e pontuação correta."
        )

    def generate_recommendation(
        self,
        provincia: str,
        cultura: str,
        data_consulta: str,
        eval_result: DecisionEvaluationResult,
    ) -> str:
        """Synthesizes the natural language agricultural advisory using LLM or formal fallback."""
        context_block = self.build_context_block(provincia, cultura, data_consulta, eval_result)
        system_prompt = self.get_system_prompt()

        user_content = (
            f"Com base nas informações agroclimáticas consolidadas abaixo, elabore a recomendação formal de orientação técnica para o agricultor:\n\n"
            f"{context_block}\n\n"
            f"Elabore a resposta mantendo rigorosamente a estrutura solicitada, o tom formal e informativo, e sem qualquer jargão técnico."
        )

        # 1. Try Google Gemini with fallback model sequence
        if self.gemini_client:
            models_to_try = [
                os.getenv("LLM_MODEL", "gemini-3.5-flash"),
                "gemini-3.5-flash",
                "gemini-3.5-flash-lite",
                "gemini-3.8-flash",
                "gemini-2.5-flash-lite",
            ]
            for model_name in models_to_try:
                try:
                    response = self.gemini_client.models.generate_content(
                        model=model_name,
                        contents=f"{system_prompt}\n\n{user_content}",
                    )
                    if response and response.text:
                        return response.text.strip()
                except Exception as e:
                    print(f"[!] Tentativa com modelo {model_name} falhou: {e}")

        # 2. Try OpenAI
        if self.openai_client:
            try:
                model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
                chat_completion = self.openai_client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=0.2,
                )
                text = chat_completion.choices[0].message.content
                if text:
                    return text.strip()
            except Exception as e:
                print(f"[!] Erro na chamada à OpenAI ({e}). Utilizando sintetizador formal local...")

        # 3. High-Fidelity Formal Local Synthesizer (Zero-Failure Fallback)
        return self._generate_local_agronomist_synthesis(provincia, cultura, eval_result)

    def _generate_local_agronomist_synthesis(
        self,
        provincia: str,
        cultura: str,
        eval_result: DecisionEvaluationResult,
    ) -> str:
        """Formal, objective, and informative agronomic synthesis in Portuguese."""
        status = eval_result.status
        m = eval_result.metricas

        if status == AdvisoryStatus.FAVORAVEL:
            text = (
                f"**FAVORÁVEL: O período atual é favorável para a sementeira de {cultura} na província do {provincia}.**\n\n"
                f"A monitorização agroclimática confirma condições propícias para o início dos trabalhos de plantio:\n\n"
                f"1. **Disponibilidade hídrica no solo:** As precipitações recentes ({m.chuva_acumulada_recente_mm:.1f} mm) "
                f"proporcionaram uma recarga adequada na camada radicular, garantindo a humidade necessária para a hidratação e germinação da semente.\n"
                f"2. **Previsão meteorológica:** A previsão para os próximos 7 dias indica acumulados de chuva em torno de {m.previsao_7dias_mm:.1f} mm, "
                f"com temperaturas favoráveis ao desenvolvimento inicial das plântulas e sem indicação de veranicos severos.\n"
                f"3. **Regularidade da época:** O padrão histórico do Planalto Central confirma este período como seguro para a instalação da cultura.\n\n"
                f"**Recomendação técnica de campo:** Antes da sementeira, recomenda-se verificar o estado do solo na profundidade de 4 a 5 cm. "
                f"Ao recolher uma amostra com a mão e pressioná-la, deve formar-se um torrão coeso que não se desmanche facilmente nem solte água em excesso. "
                f"Cubra as sementes com terra fofa para assegurar um contacto uniforme."
            )
        elif status == AdvisoryStatus.AGUARDAR:
            text = (
                f"**AGUARDAR: Recomenda-se aguardar antes de realizar a sementeira de {cultura} na província do {provincia}.**\n\n"
                f"Apesar do início das primeiras chuvas, as condições de humidade ainda requerem consolidação para evitar riscos de replante:\n\n"
                f"1. **Recarga hídrica em curso:** O solo já registou alguma precipitação ({m.chuva_acumulada_recente_mm:.1f} mm), "
                f"mas a reserva de água na zona mais profunda onde as raízes se fixarão ainda não atingiu o nível de segurança ideal. "
                f"A ocorrência de dias quentes logo após o plantio pode desidratar o gérmen da semente.\n"
                f"2. **Previsão de chuvas iminentes:** Prevê-se a ocorrência de novos eventos de precipitação nos próximos dias ({m.previsao_7dias_mm:.1f} mm), "
                f"que serão decisivos para uniformizar a humidade no perfil do solo.\n\n"
                f"**Recomendação técnica de campo:** Recomenda-se aproveitar este intervalo para finalizar a preparação da terra, alinhamento de leiras "
                f"e abertura das covas. Aguarde que as próximas chuvas infiltrem bem no solo e certifique-se de que a terra está húmida até à profundidade "
                f"de um dedo indicador antes de depositar as sementes."
            )
        else:  # DESFAVORAVEL
            text = (
                f"**NÃO PLANTAR: O momento atual é desfavorável para a sementeira de {cultura} na província do {provincia}.**\n\n"
                f"Os dados agroclimáticos indicam elevado risco de insucesso no estabelecimento da cultura:\n\n"
                f"1. **Défice hídrico no perfil do solo:** A humidade presente na zona radicular encontra-se substancialmente abaixo do limite "
                f"necessário para sustentar a germinação uniforme e a fixação das raízes.\n"
                f"2. **Precipitação insuficiente:** O volume de chuva previsto para os próximos 7 dias ({m.previsao_7dias_mm:.1f} mm) é insuficiente "
                f"para compensar a evaporação e assegurar a sobrevivência das plântulas.\n\n"
                f"**Recomendação técnica de campo:** Mantenha as sementes armazenadas em local fresco, ventilado e protegido da humidade direta. "
                f"Adie as operações de sementeira até ao estabelecimento de chuvas consistentes e verificação de humidade contínua no solo."
            )

        return text


_rag_service_instance: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
    return _rag_service_instance
