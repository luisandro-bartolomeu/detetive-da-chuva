"""Module 3: Rule-Based Decision Engine.

Combines real-time weather observations with historical agroclimatic baselines
to generate deterministic agronomic evaluations, status classification,
objective confidence scores, and structured justifications.
"""

from datetime import datetime
from typing import Dict, Any, List, Tuple
try:
    from src.schemas import AdvisoryStatus, AdvisoryMetrics, DecisionEvaluationResult
    from src.config import (
        CRITICAL_RAIN_3D_TRIGGER,
        IMMINENT_RAIN_48H_TRIGGER,
        DRY_SPELL_MAX_TEMP,
        DRY_SPELL_RAIN_LIMIT,
        CROPS,
    )
    from src.baseline_engine import get_baseline_engine
except ImportError:
    from schemas import AdvisoryStatus, AdvisoryMetrics, DecisionEvaluationResult
    from config import (
        CRITICAL_RAIN_3D_TRIGGER,
        IMMINENT_RAIN_48H_TRIGGER,
        DRY_SPELL_MAX_TEMP,
        DRY_SPELL_RAIN_LIMIT,
        CROPS,
    )
    from baseline_engine import get_baseline_engine


class DecisionEngine:
    """Deterministic agronomic rule engine for sowing suitability."""

    def __init__(self):
        self.baseline_engine = get_baseline_engine()

    def evaluate(
        self,
        provincia: str,
        cultura: str,
        data_consulta: Any,
        weather_data: Dict[str, Any],
    ) -> DecisionEvaluationResult:
        """Evaluates agroclimatic criteria and produces deterministic verdict and metrics."""
        from datetime import date
        if not data_consulta or not isinstance(data_consulta, str):
            data_consulta = date.today().isoformat()
        try:
            query_dt = datetime.strptime(str(data_consulta), "%Y-%m-%d")
        except ValueError:
            query_dt = datetime.now()

        month = query_dt.month
        week = min(max(query_dt.isocalendar()[1], 1), 52)

        # Retrieve historical baseline matrices
        month_stats = self.baseline_engine.get_province_month_stats(provincia, month)
        week_stats = self.baseline_engine.get_province_week_stats(provincia, week)

        p25_root = month_stats.get("gwetroot_p25", 0.40)
        p50_root = month_stats.get("gwetroot_p50", 0.47)
        p75_root = month_stats.get("gwetroot_p75", 0.53)
        prob_sementeira_semanal = week_stats.get("probabilidade_sementeira_pct", 50.0)

        # Real-time observations
        rain_recent = float(weather_data.get("chuva_acumulada_recente_mm", 0.0))
        rain_48h = float(weather_data.get("chuva_iminente_48h_mm", 0.0))
        rain_7d = float(weather_data.get("previsao_7dias_mm", 0.0))
        root_moisture = float(weather_data.get("humidade_solo_raiz", 0.40))
        surface_moisture = float(weather_data.get("humidade_solo_superficie", 0.40))
        t_max_7d = float(weather_data.get("temperatura_max_7d_c", 26.0))

        # Crop specific adjustments
        crop_config = CROPS.get(cultura, CROPS["Milho"])
        crop_min_rain = crop_config.get("min_rain_onset_mm", CRITICAL_RAIN_3D_TRIGGER)
        crop_crit_tmax = crop_config.get("critical_temp_max", DRY_SPELL_MAX_TEMP)

        # --- HEURISTIC EVALUATION ---
        triggers_ativados: List[str] = []
        justificacoes: List[str] = []

        # 1. Critical Root Moisture
        is_root_below_p25 = root_moisture < p25_root
        if is_root_below_p25:
            triggers_ativados.append("CRITICAL_ROOT_MOISTURE_DEFICIT")

        # 2. Recent Rain Trigger (past 3-5 days >= 20 mm OR imminent >= 25 mm within 48h)
        recent_rain_met = (rain_recent >= crop_min_rain)
        imminent_rain_met = (rain_48h >= IMMINENT_RAIN_48H_TRIGGER)
        rain_trigger_active = recent_rain_met or imminent_rain_met

        if rain_trigger_active:
            triggers_ativados.append("RECENT_RAIN_TRIGGER_SATISFIED")

        # 3. Dry Spell Risk (false onset: rain fell, but next 7d has near zero rain and high heat)
        dry_spell_risk = (
            (rain_recent >= 15.0 or is_root_below_p25)
            and (rain_7d <= DRY_SPELL_RAIN_LIMIT)
            and (t_max_7d >= crop_crit_tmax)
        )
        if dry_spell_risk:
            triggers_ativados.append("DRY_SPELL_HEAT_RISK")

        # 4. Status Determination Logic
        status, confidence_score = self._compute_status_and_score(
            is_root_below_p25=is_root_below_p25,
            root_moisture=root_moisture,
            p25_root=p25_root,
            p50_root=p50_root,
            rain_recent=rain_recent,
            rain_48h=rain_48h,
            rain_7d=rain_7d,
            dry_spell_risk=dry_spell_risk,
            recent_rain_met=recent_rain_met,
            imminent_rain_met=imminent_rain_met,
            prob_sementeira_semanal=prob_sementeira_semanal,
            t_max_7d=t_max_7d,
            month=month,
        )

        # 5. Technical Justifications
        if status == AdvisoryStatus.FAVORAVEL:
            justificacoes.append(
                f"Reserva de água na raiz favorável ({root_moisture:.2f}), superior ao limiar mínimo histórico ({p25_root:.2f})."
            )
            if recent_rain_met:
                justificacoes.append(
                    f"Acumulação recente de chuvas atingiu {rain_recent:.1f} mm nos últimos dias, garantindo solo bem humedecido."
                )
            elif imminent_rain_met:
                justificacoes.append(
                    f"Previsão de chuvas iminentes nas próximas 48 horas ({rain_48h:.1f} mm) consolida a humidade para a sementeira."
                )
            justificacoes.append(
                f"Previsão de 7 dias com {rain_7d:.1f} mm e sem risco de estiagem severa, propício para germinação uniforme do {cultura}."
            )

        elif status == AdvisoryStatus.AGUARDAR:
            if dry_spell_risk:
                justificacoes.append(
                    f"Risco de veranico / estiagem curta detectado: previsão de calor intenso ({t_max_7d:.1f}°C) e pouca chuva nos próximos 7 dias ({rain_7d:.1f} mm)."
                )
                justificacoes.append("Aguarde chuvas mais regulares para evitar a queima das sementes germinadas.")
            elif is_root_below_p25 and imminent_rain_met:
                justificacoes.append(
                    f"Humidade da raiz ({root_moisture:.2f}) ainda está em recarga. Chuvas fortes previstas ({rain_48h:.1f} mm) devem ensopar o terreno em breve."
                )
                justificacoes.append("Recomenda-se preparar as covas e aguardar 2 a 3 dias para a água infiltrar adequadamente.")
            else:
                justificacoes.append(
                    f"Chuva recente ({rain_recent:.1f} mm) ou humidade ({root_moisture:.2f}) ainda incipiente para arranque seguro da cultura de {cultura}."
                )
                justificacoes.append("Aguarde a consolidação da humidade na profundidade da semente.")

        else:  # DESFAVORAVEL
            justificacoes.append(
                f"Solo seco na profundidade da raiz ({root_moisture:.2f}), abaixo do limiar de sobrevivência hídrica ({p25_root:.2f})."
            )
            justificacoes.append(
                f"Chuva acumulada recente ({rain_recent:.1f} mm) e previsão dos próximos 7 dias ({rain_7d:.1f} mm) insuficientes."
            )
            justificacoes.append("Sementeira altamente desaconselhada sob risco crítico de perda total das sementes.")

        metrics = AdvisoryMetrics(
            chuva_acumulada_recente_mm=round(rain_recent, 1),
            humidade_solo_raiz=round(root_moisture, 3),
            previsao_7dias_mm=round(rain_7d, 1),
            humidade_solo_superficie=round(surface_moisture, 3),
            temperatura_max_prevista_c=round(t_max_7d, 1),
            p25_historico_raiz=round(p25_root, 3),
            probabilidade_sementeira_semanal=round(prob_sementeira_semanal, 1),
        )

        return DecisionEvaluationResult(
            status=status,
            score_confianca=confidence_score,
            triggers_ativados=triggers_ativados,
            justificacoes_tecnicas=justificacoes,
            metricas=metrics,
            is_fallback_weather=bool(weather_data.get("is_fallback", False)),
            detalhes_agroclimaticos={
                "provincia": provincia,
                "cultura": cultura,
                "data_consulta": data_consulta,
                "mes": month,
                "semana_iso": week,
                "p50_raiz_historico": p50_root,
                "p75_raiz_historico": p75_root,
                "chuva_media_mensal_mm": month_stats.get("chuva_media_mensal_mm", 0.0),
                "temperatura_media_c": month_stats.get("temperatura_media_c", 20.0),
            },
        )

    def _compute_status_and_score(
        self,
        is_root_below_p25: bool,
        root_moisture: float,
        p25_root: float,
        p50_root: float,
        rain_recent: float,
        rain_48h: float,
        rain_7d: float,
        dry_spell_risk: bool,
        recent_rain_met: bool,
        imminent_rain_met: bool,
        prob_sementeira_semanal: float,
        t_max_7d: float,
        month: int,
    ) -> Tuple[AdvisoryStatus, int]:
        """Calculates deterministic status and confidence score."""
        # Check dry season in Planalto Central (May-August: months 5, 6, 7, 8)
        is_dry_season = month in [5, 6, 7, 8]

        # Case 1: Dry season or critical moisture deficit with no upcoming rain
        if is_dry_season or (is_root_below_p25 and not imminent_rain_met and rain_7d < 12.0):
            # DESFAVORAVEL
            # Confidence is high when conditions are unequivocally dry
            base_score = 80
            if root_moisture < p25_root * 0.85:
                base_score += 10
            if rain_7d < 5.0:
                base_score += 5
            score = min(max(base_score, 65), 95)
            return AdvisoryStatus.DESFAVORAVEL, score

        # Case 2: Acute False Onset / Dry Spell Risk
        if dry_spell_risk:
            # AGUARDAR (Farmer should not sow into a heat trap)
            score = 85
            return AdvisoryStatus.AGUARDAR, score

        # Case 3: Root moisture below P25, but strong imminent rain coming in 48h
        if is_root_below_p25 and imminent_rain_met:
            # AGUARDAR: Prepare land and wait for rain to soak in
            score = 82
            return AdvisoryStatus.AGUARDAR, score

        # Case 4: Root moisture is good (>= P25) and rain trigger satisfied, forecast favorable
        if not is_root_below_p25 and (recent_rain_met or imminent_rain_met) and (rain_7d >= 15.0 or rain_recent >= 30.0):
            # FAVORAVEL
            # Base score starting from historical stability
            score = int(60 + (prob_sementeira_semanal * 0.2))
            if root_moisture >= p50_root:
                score += 10
            if rain_recent >= 25.0:
                score += 8
            if rain_7d >= 20.0:
                score += 5
            score = min(max(score, 70), 95)
            return AdvisoryStatus.FAVORAVEL, score

        # Case 5: Root moisture >= P25, but recent rain hasn't quite hit trigger and forecast moderate
        if not is_root_below_p25 and rain_7d >= 20.0:
            # FAVORAVEL (moisture is already good in root zone and good rain ahead)
            score = 75
            return AdvisoryStatus.FAVORAVEL, score

        # Case 6: Intermediate conditions (e.g. erratic or borderline)
        # AGUARDAR: Safer for smallholders to wait for solid accumulation
        score = 72
        return AdvisoryStatus.AGUARDAR, score


_decision_engine_instance = None


def get_decision_engine() -> DecisionEngine:
    global _decision_engine_instance
    if _decision_engine_instance is None:
        _decision_engine_instance = DecisionEngine()
    return _decision_engine_instance
