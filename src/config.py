"""Configuration settings for Agricultural Decision Support System.

Planalto Central de Angola (Huambo, Bié, Huíla).
"""

from pathlib import Path
from typing import Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
CROPS: Dict[str, Dict[str, Any]] = {
    "Milho": {
        "name": "Milho",
        "scientific_name": "Zea mays",
        "min_rain_onset_mm": 20.0,
        "optimal_root_moisture": 0.40,
        "critical_temp_max": 32.0,
        "soil_depth_cm": 5,
        "notes": "Cultura base de segurança alimentar no Planalto Central.",
    },
    "Feijão": {
        "name": "Feijão",
        "scientific_name": "Phaseolus vulgaris",
        "min_rain_onset_mm": 18.0,
        "optimal_root_moisture": 0.38,
        "critical_temp_max": 30.0,
        "soil_depth_cm": 4,
        "notes": "Muito sensível ao encharcamento prolongado e a veranicos pós-germinação.",
    },
    "Soja": {
        "name": "Soja",
        "scientific_name": "Glycine max",
        "min_rain_onset_mm": 22.0,
        "optimal_root_moisture": 0.42,
        "critical_temp_max": 33.0,
        "soil_depth_cm": 4,
        "notes": "Exige humidade contínua na sementeira para boa taxa de emergência.",
    },
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
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto")  # 'gemini', 'openai', or 'auto'
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")

# Server Configuration
SERVER_HOST = os.getenv("HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("PORT", 8000))
