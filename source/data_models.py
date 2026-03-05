# source/data_models.py
from dataclasses import dataclass
from typing import Optional, Dict, Any
import pandas as pd


@dataclass
class PVGISImportResult:
    """Data class to hold PVGIS import results"""
    source: str  # "PVGIS"
    mode: str  # "HOURLY" or "TMY"
    latitude: float
    longitude: float
    hourly_data: pd.DataFrame
    metadata: Dict[str, Any]
    monthly_totals: Optional[Dict] = None
    annual_total_kwh: Optional[float] = None
    database: Optional[str] = None