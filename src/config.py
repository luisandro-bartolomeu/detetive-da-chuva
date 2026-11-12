"""Configuration settings for Agricultural Decision Support System.

Planalto Central de Angola (Huambo, Bié, Huíla).
"""

from pathlib import Path
from typing import Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Environment mode (production disables Swagger / OpenAPI / ReDoc)
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
IS_PRODUCTION = ENVIRONMENT in ["production", "prod"]

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR

# Target Provinces and Coordinates (Planalto Central de Angola)
PROVINCES: Dict[str, Dict[str, Any]] = {
    "Huambo": {
        "id": "huambo",
        "name": "Huambo",
        "latitude": -12.7761,
        "longitude": 15.7392,
        "raw_file": "nasa_power_raw_huambo_2000_2024.json",
        "elevation_m": 1700,
        "agroecological_zone": "Planalto Central Tropical de Altitude",
    },
    "Bié": {
        "id": "bie",
        "name": "Bié",
        "latitude": -12.3833,
        "longitude": 16.9333,
        "raw_file": "nasa_power_raw_bie_2000_2024.json",
        "elevation_m": 1650,
        "agroecological_zone": "Planalto Central Oriental",
    },
    "Huíla": {
        "id": "huila",
        "name": "Huíla",
        "latitude": -14.9172,
        "longitude": 13.5414,
        "raw_file": "nasa_power_raw_huila_2000_2024.json",
        "elevation_m": 1760,
        "agroecological_zone": "Planalto de Humpata e Lubango",
    },
}

# Supported Crops and Agronomic Thresholds
CROP_PROFILES: Dict[str, Dict[str, Any]] = {
    "Milho": {
        "id": "milho",
        "name": "Milho",
        "scientific_name": "Zea mays",
        "icon": "🌽",
        "min_rain_3d_mm": 20.0,
        "min_monthly_rain_mm": 110.0,
        "root_moisture_quantile_floor": "P25",
        "min_absolute_root_moisture": 0.35,
        "optimal_temp_range": (18.0, 32.0),
        "critical_temp_max": 32.0,
        "waterlogging_limit": 0.85,
        "sowing_depth_cm": 5,
        "notes": "Cultura base de segurança alimentar no Planalto Central. Exige solo húmido até 5 cm e boa reserva radicular.",
    },
    "Feijão": {
        "id": "feijao",
        "name": "Feijão",
        "scientific_name": "Phaseolus vulgaris",
        "icon": "🫘",
        "min_rain_3d_mm": 15.0,
        "min_monthly_rain_mm": 80.0,
        "root_moisture_quantile_floor": "P25",
        "min_absolute_root_moisture": 0.30,
        "optimal_temp_range": (15.0, 29.0),
        "critical_temp_max": 29.0,
        "waterlogging_limit": 0.72,  # CRÍTICO: apodrece com facilidade em solo encharcado
        "sowing_depth_cm": 4,
        "notes": "Menor exigência inicial de água (15 mm), ciclo curto, mas muito vulnerável ao encharcamento (>0.72) e calor acima de 29°C.",
    },
    "Soja": {
        "id": "soja",
        "name": "Soja",
        "scientific_name": "Glycine max",
        "icon": "🌱",
        "min_rain_3d_mm": 25.0,
        "min_monthly_rain_mm": 130.0,
        "root_moisture_quantile_floor": "P50",
        "min_absolute_root_moisture": 0.40,
        "optimal_temp_range": (20.0, 30.0),
        "critical_temp_max": 33.0,
        "waterlogging_limit": 0.80,
        "sowing_depth_cm": 4,
        "notes": "Semente oleaginosa que exige alta absorção hídrica para germinar (~50% do seu peso). Requer humidade radicular robusta (>=0.40).",
    },
}

# Alias for backwards compatibility
CROPS: Dict[str, Dict[str, Any]] = CROP_PROFILES

# Agricultural Municipalities in the Central Plateau (Huambo, Bié, Huíla)
MUNICIPALITIES: Dict[str, Dict[str, Any]] = {
    # Huambo
    "huambo": {"name": "Huambo", "provincia": "Huambo", "latitude": -12.7761, "longitude": 15.7392},
    "caala": {"name": "Caála", "provincia": "Huambo", "latitude": -12.8525, "longitude": 15.5606},
    "bailundo": {"name": "Bailundo", "provincia": "Huambo", "latitude": -12.1936, "longitude": 15.8697},
    "chicala-cholohanga": {"name": "Chicala-Cholohanga", "provincia": "Huambo", "latitude": -12.9833, "longitude": 16.0333},
    "longonjo": {"name": "Longonjo", "provincia": "Huambo", "latitude": -12.9067, "longitude": 15.2533},
    "ukuma": {"name": "Ukuma", "provincia": "Huambo", "latitude": -12.8500, "longitude": 15.0667},
    "ekunha": {"name": "Ekunha", "provincia": "Huambo", "latitude": -12.6739, "longitude": 15.5133},
    # Bié
    "bie": {"name": "Bié", "provincia": "Bié", "latitude": -12.3833, "longitude": 16.9333},
    "kuito": {"name": "Kuito", "provincia": "Bié", "latitude": -12.3833, "longitude": 16.9333},
    "camacupa": {"name": "Camacupa", "provincia": "Bié", "latitude": -12.0167, "longitude": 17.4833},
    "catabola": {"name": "Catabola", "provincia": "Bié", "latitude": -12.1500, "longitude": 17.2833},
    "chinguar": {"name": "Chinguar", "provincia": "Bié", "latitude": -12.5833, "longitude": 16.3500},
    "andulo": {"name": "Andulo", "provincia": "Bié", "latitude": -11.4833, "longitude": 16.9667},
    "chitembo": {"name": "Chitembo", "provincia": "Bié", "latitude": -13.5167, "longitude": 16.7500},
    # Huíla
    "huila": {"name": "Huíla", "provincia": "Huíla", "latitude": -14.9172, "longitude": 13.5414},
    "lubango": {"name": "Lubango", "provincia": "Huíla", "latitude": -14.9172, "longitude": 13.5414},
    "matala": {"name": "Matala", "provincia": "Huíla", "latitude": -15.6833, "longitude": 15.0333},
    "caconda": {"name": "Caconda", "provincia": "Huíla", "latitude": -13.7333, "longitude": 15.0667},
    "chibia": {"name": "Chibia", "provincia": "Huíla", "latitude": -15.1833, "longitude": 13.6833},
    "caluquembe": {"name": "Caluquembe", "provincia": "Huíla", "latitude": -13.7833, "longitude": 14.6833},
    "quilengues": {"name": "Quilengues", "provincia": "Huíla", "latitude": -14.0833, "longitude": 14.0833},
}

# Processed Baseline File Path
PROCESSED_BASELINE_PATH = DATA_DIR / "processed_baseline.json"

# Decision Thresholds
CRITICAL_RAIN_3D_TRIGGER = 20.0   # mm in 3 days
IMMINENT_RAIN_48H_TRIGGER = 25.0  # mm forecast in 48 hours
DRY_SPELL_MAX_TEMP = 32.0         # Celsius
DRY_SPELL_RAIN_LIMIT = 2.0        # mm in 7 days forecast

# Open-Meteo Configuration
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_REQUEST_TIMEOUT = 8.0  # seconds

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.5-flash")

# Server Configuration
SERVER_HOST = os.getenv("HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("PORT", 8000))
