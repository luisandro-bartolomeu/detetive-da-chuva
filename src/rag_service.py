"""Module 4: Knowledge Chunking & RAG Synthesis.

Assembles dynamic context blocks from statistical baselines and real-time decision metrics,
prompts LLMs (Gemini / OpenAI) with strict agricultural extension instructions,
and provides a resilient deterministic agronomist synthesis fallback.
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime

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

        # Translate status into agronomic verdict for smallholders
        status_verdicts = {
            AdvisoryStatus.FAVORAVEL: "FAVORÁVEL (Pode Semear)",
            AdvisoryStatus.AGUARDAR: "AGUARDAR (Aguardar consolidação das chuvas / Preparar cova)",
            AdvisoryStatus.DESFAVORAVEL: "NÃO PLANTAR (Desfavorável / Alto risco de perda de semente)",
        }
        verdict_str = status_verdicts.get(eval_result.status, "AGUARDAR")

        mes_nome = datetime.strptime(data_consulta, "%Y-%m-%d").strftime("%B") if "-" in data_consulta else "Novembro"
        # Portuguese month name mapping
        meses_pt = {
            "January": "Janeiro", "February": "Fevereiro", "March": "Março",
            "April": "Abril", "May": "Maio", "June": "Junho",
            "July": "Julho", "August": "Agosto", "September": "Setembro",
            "October": "Outubro", "November": "Novembro", "December": "Dezembro"
        }
        mes_nome_pt = meses_pt.get(mes_nome, mes_nome)

        context_lines = [
            f"### CONTEXTO AGROCLIMÁTICO REGIONAL - PLANALTO CENTRAL DE ANGOLA",
            f"- **Província:** {provincia} (Zona Agroecológica: {PROVINCES.get(provincia, {}).get('agroecological_zone', 'Planalto Central')})",
            f"- **Cultura Avaliada:** {cultura}",
            f"- **Data da Consulta:** {data_consulta} (Mês: {mes_nome_pt}, Semana Agrícola: {details.get('semana_iso', 'N/A')})",
            "",
            f"#### 1. Linha de Base Histórica da Região (NASA POWER 2000-2024)",
            f"- Chuva média histórica deste mês: {details.get('chuva_media_mensal_mm', 0):.1f} mm/mês",
            f"- Probabilidade histórica de sementeira favorável nesta semana: {m.probabilidade_sementeira_semanal or 50:.1f}%",
            f"- Temperatura média típica: {details.get('temperatura_media_c', 20):.1f} °C",
            "",
            f"#### 2. Condições Meteorológicas Observadas e Previsão Imediata (Open-Meteo)",
            f"- Chuva acumulada recente (últimos 3-5 dias): {m.chuva_acumulada_recente_mm:.1f} mm",
            f"- Previsão de chuva acumulada para os próximos 7 dias: {m.previsao_7dias_mm:.1f} mm",
            f"- Temperatura máxima prevista nos próximos 7 dias: {m.temperatura_max_prevista_c or 26:.1f} °C",
            f"- Nível de humidade na zona das raízes: {m.humidade_solo_raiz:.3f} (Reserva mínima segura: {m.p25_historico_raiz or 0.40:.3f})",
            f"- Nível de humidade na camada superficial (0-7 cm): {m.humidade_solo_superficie or 0.40:.3f}",
            "",
            f"#### 3. Avaliação Técnica Determinística do Sistema",
            f"- Veredito Oficial: **{verdict_str}**",
            f"- Nível de Confiança da Análise: {eval_result.score_confianca}%",
            f"- Gatilhos Agronómicos Identificados: {', '.join(eval_result.triggers_ativados) or 'Condições estáveis'}",
            f"- Justificações Técnicas Internas:",
        ]

        for just in eval_result.justificacoes_tecnicas:
            context_lines.append(f"  * {just}")

        return "\n".join(context_lines)

    def get_system_prompt(self) -> str:
        """Returns the strict system instructions for the LLM."""
        return (
            "És um Engenheiro Agrónomo e Extensionista Rural sénior com profunda experiência no Planalto Central de Angola "
            "(Huambo, Bié e Huíla). O teu papel é orientar famílias camponesas e pequenos produtores agrícolas sobre o "
            "momento seguro para a sementeira das suas culturas (como milho, feijão ou soja).\n\n"
            "DIRETRIZES FUNDAMENTAIS DE COMUNICAÇÃO:\n"
            "1. LINGUAGEM E TOM: Fala com clareza, respeito, calor humano e empatia, usando o português simples e acolhedor de Angola. "
            "Usa termos familiares aos agricultores angolanos, como 'terra bem húmida', 'reserva de água da raiz', "
            "'época das chuvas', 'fazer a covinha', 'tempo seco', 'molha da sementeira'.\n"
            "2. PROIBIÇÃO ABSOLUTA DE JARGÃO TÉCNICO: NUNCA mencione termos científicos, matemáticos ou computacionais, como: "
            "'Mann-Kendall', 'SARIMA', 'p-valor', 'P25', 'GWETROOT', 'GWETTOP', 'APIs', 'Open-Meteo', 'NASA POWER', 'percentis', "
            "'algoritmo', ou 'banco de dados'. Transforma todas as medições em explicações práticas da terra e do céu.\n"
            "3. ESTRUTURA OBRIGATÓRIA DA RESPOSTA:\n"
            "   A) PRIMEIRA FRASE (Veredito em destaque): Começa de forma direta com uma das palavras-chave em maiúsculas:\n"
            "      - Se a análise for favorável: '**FAVORÁVEL**: É boa altura para deitar a semente à terra.'\n"
            "      - Se for para esperar: '**AGUARDAR**: Ainda não é momento de semear; prepare o terreno e espere mais um pouco.'\n"
            "      - Se for desfavorável: '**NÃO PLANTAR**: O tempo e a terra não estão seguros para a sementeira agora.'\n"
            "   B) 2 A 3 JUSTIFICAÇÕES DIRETAS: Explica em parágrafos curtos a estabilidade da época das chuvas na província, "
            "a quantidade de água guardada no solo e o que se espera do tempo nos próximos dias.\n"
            "   C) DICA PRÁTICA DE CAMPO: Dá um conselho tradicional prático que o camponês pode testar com as próprias mãos no campo "
            "(ex.: enfiar o dedo indicador até à profundidade da junta para sentir a humidade fresca, ou apertar um punhado de terra "
            "na mão para ver se forma torrão sem escorrer água).\n\n"
            "Sê objetivo, encorajador e prático. O agricultor confia na tua palavra para proteger as suas sementes."
        )

    def generate_recommendation(
        self,
        provincia: str,
        cultura: str,
        data_consulta: str,
        eval_result: DecisionEvaluationResult,
    ) -> str:
        """Synthesizes the natural language agricultural advisory using LLM or robust fallback."""
        context_block = self.build_context_block(provincia, cultura, data_consulta, eval_result)
        system_prompt = self.get_system_prompt()

        user_content = (
            f"Com base nas informações agroclimáticas abaixo, elabora a recomendação de extensão rural para o camponês:\n\n"
            f"{context_block}\n\n"
            f"Elabora agora a resposta ao agricultor, respeitando rigorosamente a estrutura e todas as diretrizes de linguagem."
        )

        # 1. Try Gemini
        if self.gemini_client:
            try:
                # Use models like gemini-2.5-flash or gemini-1.5-flash
                model_name = os.getenv("LLM_MODEL", "gemini-2.5-flash")
                response = self.gemini_client.models.generate_content(
                    model=model_name,
                    contents=f"{system_prompt}\n\n{user_content}",
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                print(f"[!] Erro na chamada ao Google Gemini ({e}). Tentando alternativas...")

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
                    temperature=0.3,
                )
                text = chat_completion.choices[0].message.content
                if text:
                    return text.strip()
            except Exception as e:
                print(f"[!] Erro na chamada à OpenAI ({e}). Utilizando sintetizador agronómico local...")

        # 3. High-Fidelity Local Agronomist Synthesizer (Zero-Failure Fallback)
        return self._generate_local_agronomist_synthesis(provincia, cultura, eval_result)

    def _generate_local_agronomist_synthesis(
        self,
        provincia: str,
        cultura: str,
        eval_result: DecisionEvaluationResult,
    ) -> str:
        """High quality deterministic agronomic synthesis in authentic Angolan Portuguese."""
        status = eval_result.status
        m = eval_result.metricas
        conf = eval_result.score_confianca

        if status == AdvisoryStatus.FAVORAVEL:
            text = (
                f"**FAVORÁVEL: É momento oportuno para semear o seu {cultura} no {provincia}!**\n\n"
                f"A época das chuvas está a responder com firmeza e as condições da terra estão adequadas para lançar a semente:\n\n"
                f"1. **Reserva da terra:** O chão já bebeu água suficiente ({m.chuva_acumulada_recente_mm:.1f} mm recentemente) e "
                f"a humidade em profundidade está fresca e bem estabelecida, garantindo que o grão não irá secar após o inchaço.\n"
                f"2. **Céu favorável:** A previsão para a próxima semana indica continuidade de boas chuvas ({m.previsao_7dias_mm:.1f} mm), "
                f"com temperaturas amenas que ajudam a planta a romper a terra com força e vigor.\n"
                f"3. **Garantia da época:** Historicamente no Planalto Central, este período oferece estabilidade climática para o {cultura}.\n\n"
                f"**Dica prática do Engenheiro:** Antes de colocar a semente na cova, faça o teste do punhado: cave com a mão até à profundidade "
                f"de um dedo indicador (cerca de 5 cm), retire uma mão cheia de terra e aperte bem. Se formar um torrão firme que não esfarela "
                f"e que não escorre água pelos dedos, a terra está no ponto ideal! Cubra a semente com terra leve e solta."
            )
        elif status == AdvisoryStatus.AGUARDAR:
            text = (
                f"**AGUARDAR: Tenha calma, meu irmão camponês; ainda não é a melhor hora para deitar a semente à terra no {provincia}.**\n\n"
                f"A terra está a começar a despertar, mas ainda requer cautela para não perdermos o trabalho nem as sementes:\n\n"
                f"1. **Chão ainda a recarregar:** Embora já tenha caído alguma chuva ({m.chuva_acumulada_recente_mm:.1f} mm), "
                f"a reserva de água mais abaixo onde a raiz vai crescer ainda está rasa. Se plantarmos agora com o sol quente da tarde, "
                f"o calor pode secar o grelo do {cultura}.\n"
                f"2. **Tempo à vista:** Esperam-se mais chuvas nos próximos dias ({m.previsao_7dias_mm:.1f} mm previstos). "
                f"É mais seguro deixar essa chuva cair e ensopar bem a camada da raiz.\n\n"
                f"**Dica prática do Engenheiro:** Aproveite estes próximos 2 a 3 dias para adiantar o trabalho: limpe as leiras, abra as covas "
                f"e deixe as sementes prontas no celeiro. Assim que cair a próxima chuva forte e o chão ficar empapado até à fundura de um dedo, "
                f"a terra estará pronta para receber o grão com segurança."
            )
        else:  # DESFAVORAVEL
            text = (
                f"**NÃO PLANTAR: O tempo e a terra não estão seguros para a sementeira de {cultura} no {provincia} neste momento.**\n\n"
                f"O risco de perda das sementes é muito alto se semear agora, por motivos claros:\n\n"
                f"1. **Solo seco em profundidade:** A terra não tem humidade acumulada na zona onde a raiz precisa de beber água. "
                f"A semente corre sério risco de grelar com um orvalho fraco e morrer com o sol logo de seguida.\n"
                f"2. **Pouca chuva prevista:** O céu não promete água suficiente para a próxima semana ({m.previsao_7dias_mm:.1f} mm previstos), "
                f"havendo perigo de as plantas não resistirem à sede.\n\n"
                f"**Dica prática do Engenheiro:** Guarde as suas sementes num lugar fresco e seco. Vá acompanhando os sinais da natureza e "
                f"aguarde que a chuva caia firme durante dois ou três dias seguidos antes de voltar a pensar na sementeira. A paciência poupa o suor "
                f"e garante a colheita."
            )

        return text


_rag_service_instance: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
    return _rag_service_instance
