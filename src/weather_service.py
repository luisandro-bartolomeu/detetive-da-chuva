"""Module 2: Real-Time Weather Integration.

Fetches real-time and near-term forecast data using Open-Meteo API for Angolan provinces,
with past 7 days observed rainfall, current root/surface soil moisture, and next 7 days forecast.
Includes caching and robust statistical fallback to historical climatological baseline.
"""

from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional
import time
import requests

try:
    from src.config import (
        PROVINCES,
        OPEN_METEO_URL,
        WEATHER_REQUEST_TIMEOUT,
    )
    from src.baseline_engine import get_baseline_engine
except ImportError:
    from config import (
        PROVINCES,
        OPEN_METEO_URL,
        WEATHER_REQUEST_TIMEOUT,
    )
    from baseline_engine import get_baseline_engine


class WeatherService:
    """Handles real-time and forecast weather data retrieval with graceful fallback."""

    def __init__(self, timeout: float = WEATHER_REQUEST_TIMEOUT):
        self.timeout = timeout
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl_seconds = 600  # 10 minutes cache

    def _get_cache_key(self, provincia: str, query_date: str) -> str:
        return f"{provincia.lower()}_{query_date}"

    def fetch_weather(self, provincia: str, query_date: str) -> Dict[str, Any]:
        """Fetches live/forecast weather from Open-Meteo, falling back to baseline if needed."""
        cache_key = self._get_cache_key(provincia, query_date)
        now = time.time()

        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if now - entry["timestamp"] < self.cache_ttl_seconds:
                return entry["data"]

        prov_info = PROVINCES.get(provincia)
        if not prov_info:
            for p_name, p_data in PROVINCES.items():
                if p_name.lower() == provincia.lower():
                    prov_info = p_data
                    break

        if not prov_info:
            raise ValueError(f"Província não suportada: {provincia}")

        lat = prov_info["latitude"]
        lon = prov_info["longitude"]

        try:
            live_data = self._call_open_meteo(lat, lon, query_date)
            parsed_weather = self._parse_open_meteo_response(live_data, query_date)
            parsed_weather["is_fallback"] = False
            parsed_weather["provincia"] = provincia
            self.cache[cache_key] = {"timestamp": now, "data": parsed_weather}
            return parsed_weather

        except Exception as e:
            print(f"[!] Aviso: Chamada à Open-Meteo falhou ({e}). Utilizando fallback climatológico da linha de base.")
            fallback_weather = self._generate_fallback(provincia, query_date, error_message=str(e))
            self.cache[cache_key] = {"timestamp": now, "data": fallback_weather}
            return fallback_weather

    def _call_open_meteo(self, lat: float, lon: float, query_date: str) -> Dict[str, Any]:
        """Executes HTTP request to Open-Meteo API."""
        params = {
            "latitude": lat,
            "longitude": lon,
            "past_days": 7,
            "forecast_days": 7,
            "daily": ["precipitation_sum", "temperature_2m_max", "temperature_2m_min"],
            "hourly": ["soil_moisture_0_to_7cm", "soil_moisture_7_to_28cm", "soil_moisture_28_to_100cm"],
            "timezone": "Africa/Luanda",
        }

        response = requests.get(OPEN_METEO_URL, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _parse_open_meteo_response(self, data: Dict[str, Any], query_date: str) -> Dict[str, Any]:
        """Parses raw Open-Meteo payload into structured agricultural metrics."""
        daily = data.get("daily", {})
        hourly = data.get("hourly", {})

        dates = daily.get("time", [])
        precip = daily.get("precipitation_sum", [])
        t_max = daily.get("temperature_2m_max", [])
        t_min = daily.get("temperature_2m_min", [])

        # Identify today's index in daily series
        # With past_days=7, index 7 is usually today
        today_str = query_date
        today_idx = 7
        if today_str in dates:
            today_idx = dates.index(today_str)
        elif len(dates) > 7:
            today_idx = 7

        # Past 3 to 5 days rainfall calculation
        past_start_3d = max(0, today_idx - 3)
        past_start_5d = max(0, today_idx - 5)

        rain_past_3d = sum([p for p in precip[past_start_3d:today_idx] if p is not None])
        rain_past_5d = sum([p for p in precip[past_start_5d:today_idx] if p is not None])
        # Choose the representative recent accumulation (max of 3d and 5d to capture recent trigger)
        rain_recent = max(rain_past_3d, rain_past_5d)

        # Imminent rain (next 48h, i.e. today + tomorrow)
        imminent_end = min(len(precip), today_idx + 2)
        rain_imminent_48h = sum([p for p in precip[today_idx:imminent_end] if p is not None])

        # Next 7 days forecast precipitation and temperatures
        forecast_end = min(len(precip), today_idx + 7)
        forecast_precip_slice = [p for p in precip[today_idx:forecast_end] if p is not None]
        rain_forecast_7d = sum(forecast_precip_slice)

        forecast_tmax_slice = [t for t in t_max[today_idx:forecast_end] if t is not None]
        forecast_tmin_slice = [t for t in t_min[today_idx:forecast_end] if t is not None]

        max_temp_7d = max(forecast_tmax_slice) if forecast_tmax_slice else 28.0
        min_temp_7d = min(forecast_tmin_slice) if forecast_tmin_slice else 15.0
        avg_temp_7d = (max_temp_7d + min_temp_7d) / 2.0

        # Current Soil Moisture from hourly readings (use recent valid values)
        sm_0_7_list = [x for x in hourly.get("soil_moisture_0_to_7cm", []) if x is not None]
        sm_7_28_list = [x for x in hourly.get("soil_moisture_7_to_28cm", []) if x is not None]
        sm_28_100_list = [x for x in hourly.get("soil_moisture_28_to_100cm", []) if x is not None]

        # Use latest available reading (or average of the last 6 hours)
        surface_moisture = float(sum(sm_0_7_list[-6:]) / len(sm_0_7_list[-6:])) if sm_0_7_list else 0.45

        # Root zone moisture: Open-Meteo 7-28 cm and 28-100 cm combined
        if sm_7_28_list and sm_28_100_list:
            root_7_28 = sum(sm_7_28_list[-6:]) / len(sm_7_28_list[-6:])
            root_28_100 = sum(sm_28_100_list[-6:]) / len(sm_28_100_list[-6:])
            root_moisture = float((root_7_28 * 0.6) + (root_28_100 * 0.4))
        elif sm_7_28_list:
            root_moisture = float(sum(sm_7_28_list[-6:]) / len(sm_7_28_list[-6:]))
        else:
            root_moisture = 0.42

        return {
            "chuva_acumulada_recente_mm": round(rain_recent, 1),
            "chuva_acumulada_3d_mm": round(rain_past_3d, 1),
            "chuva_acumulada_5d_mm": round(rain_past_5d, 1),
            "chuva_iminente_48h_mm": round(rain_imminent_48h, 1),
            "previsao_7dias_mm": round(rain_forecast_7d, 1),
            "temperatura_max_7d_c": round(max_temp_7d, 1),
            "temperatura_min_7d_c": round(min_temp_7d, 1),
            "temperatura_media_7d_c": round(avg_temp_7d, 1),
            "humidade_solo_superficie": round(surface_moisture, 3),
            "humidade_solo_raiz": round(root_moisture, 3),
            "datas_previsao": dates[today_idx:forecast_end],
            "chuva_diaria_previsao": forecast_precip_slice,
        }

    def _generate_fallback(self, provincia: str, query_date: str, error_message: str = "") -> Dict[str, Any]:
        """Generates statistical climatological fallback metrics when Open-Meteo is unreachable."""
        try:
            target_dt = datetime.strptime(query_date, "%Y-%m-%d")
        except ValueError:
            target_dt = datetime.now()

        month = target_dt.month
        week = target_dt.isocalendar()[1]

        engine = get_baseline_engine()
        m_stats = engine.get_province_month_stats(provincia, month)
        w_stats = engine.get_province_week_stats(provincia, week)

        # Baseline climatological estimation
        avg_monthly_rain = m_stats.get("chuva_media_mensal_mm", 150.0)
        daily_rain_rate = avg_monthly_rain / 30.0

        # Estimate typical 3-day and 7-day rainfall for that month
        rain_recent = round(daily_rain_rate * 3.5, 1)
        rain_48h = round(daily_rain_rate * 2.0, 1)
        rain_7d = round(daily_rain_rate * 7.0, 1)

        root_moisture = m_stats.get("gwetroot_p50", 0.45)
        surface_moisture = m_stats.get("gwettop_media", 0.48)
        t_max = m_stats.get("temperatura_max_c", 26.5)
        t_min = m_stats.get("temperatura_min_c", 15.5)

        return {
            "chuva_acumulada_recente_mm": rain_recent,
            "chuva_acumulada_3d_mm": round(daily_rain_rate * 3.0, 1),
            "chuva_acumulada_5d_mm": round(daily_rain_rate * 5.0, 1),
            "chuva_iminente_48h_mm": rain_48h,
            "previsao_7dias_mm": rain_7d,
            "temperatura_max_7d_c": t_max,
            "temperatura_min_7d_c": t_min,
            "temperatura_media_7d_c": round((t_max + t_min) / 2.0, 1),
            "humidade_solo_superficie": surface_moisture,
            "humidade_solo_raiz": root_moisture,
            "is_fallback": True,
            "fallback_reason": f"Open-Meteo indisponível: {error_message}",
            "provincia": provincia,
        }


_weather_instance: Optional[WeatherService] = None


def get_weather_service() -> WeatherService:
    global _weather_instance
    if _weather_instance is None:
        _weather_instance = WeatherService()
    return _weather_instance
