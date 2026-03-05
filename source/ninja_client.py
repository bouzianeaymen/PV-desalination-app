import requests
import pandas as pd
import json
from typing import Dict, List, Optional

NINJA_BASE_URL = "https://www.renewables.ninja/api/"
PV_ENDPOINT = NINJA_BASE_URL + "data/pv"
WIND_ENDPOINT = NINJA_BASE_URL + "data/wind"
MODELS_ENDPOINT = NINJA_BASE_URL + "models"

# Hardcoded API token - configured for automatic use
DEFAULT_NINJA_TOKEN = "92fffc450a4b4f379d5499c0205d161a65a091a6"


# Cache for models metadata
_models_cache = None


def fetch_ninja_models(token: str = None) -> List[Dict]:
    """
    Fetch all available models metadata from Renewables.ninja API.
    
    Args:
        token: API authentication token (optional)
    
    Returns:
        List of model metadata dictionaries
    """
    global _models_cache
    
    if _models_cache is not None:
        return _models_cache
    
    if not token:
        token = DEFAULT_NINJA_TOKEN
    
    try:
        session = requests.Session()
        session.headers = {"Authorization": f"Token {token}"}
        
        response = session.get(MODELS_ENDPOINT, timeout=30)
        response.raise_for_status()
        
        _models_cache = response.json()
        return _models_cache
        
    except Exception as e:
        raise Exception(f"Failed to fetch models: {str(e)}")


def get_wind_model_metadata(token: str = None) -> Dict:
    """
    Get wind model metadata including fields and defaults.
    
    Args:
        token: API authentication token (optional)
    
    Returns:
        Wind model metadata dictionary
    """
    models = fetch_ninja_models(token)
    
    for model in models:
        if model.get("id") == "wind":
            return model
    
    raise Exception("Wind model not found in API models")


def fetch_ninja_wind_turbines(token: str = None) -> List[str]:
    """
    Fetch available wind turbine models from API.
    
    Args:
        token: API authentication token (optional)
    
    Returns:
        List of turbine model names
    """
    try:
        wind_model = get_wind_model_metadata(token)
        
        # Find the turbine field
        for field in wind_model.get("fields", []):
            if field.get("id") == "turbine":
                options = field.get("options", [])
                return [opt.get("value") for opt in options if opt.get("value")]
        
        return []
        
    except Exception as e:
        # Return default turbine list as fallback
        return ["Vestas V90 2000"]


def get_wind_year_range(token: str = None) -> Dict:
    """
    Get valid year range for wind data from API.
    
    Args:
        token: API authentication token (optional)
    
    Returns:
        Dict with 'min' and 'max' years
    """
    try:
        wind_model = get_wind_model_metadata(token)
        
        # Get date range from first dataset
        datasets = wind_model.get("datasets", [])
        if datasets and len(datasets) > 0:
            daterange = datasets[0].get("daterange", [])
            if len(daterange) >= 2:
                start_date = daterange[0]  # e.g., "2019-01-01"
                end_date = daterange[1]    # e.g., "2019-12-31"
                start_year = int(start_date.split("-")[0])
                end_year = int(end_date.split("-")[0])
                return {"min": start_year, "max": end_year, "source": "api"}
        
        # Fallback
        return {"min": 2019, "max": 2019, "source": "fallback"}
        
    except Exception:
        return {"min": 2019, "max": 2019, "source": "fallback"}


# Known column names for wind speed in Ninja Wind API raw response
# Ninja may return "wind speed", "wind_speed", "wind", "wind10m", "ws", etc.
WIND_SPEED_COL_ALIASES = ("wind speed", "wind_speed", "wind", "ws", "windspeed", "wind10m", "wind50m", "wind100m")


def fetch_ninja_wind_speed(
    latitude: float,
    longitude: float,
    year: int,
    hub_height_m: float,
    capacity_kw: float,
    turbine_model: str = "Vestas V90 2000",
    token: str = None
) -> Optional[pd.Series]:
    """
    Fetch wind speed only from Renewables.ninja Wind API (always MERRA-2, raw=true).
    Returns a Series with values for merging into PV hourly data (index = wind timestamps).
    """
    result = fetch_ninja_wind(
        latitude=latitude,
        longitude=longitude,
        year=year,
        capacity_kw=capacity_kw,
        hub_height_m=hub_height_m,
        turbine_model=turbine_model,
        include_raw=True,
        token=token
    )
    df = result.get("hourly_data")
    if df is None or df.empty:
        return None
    # Find wind speed column - try exact aliases first
    for alias in WIND_SPEED_COL_ALIASES:
        for c in df.columns:
            cnorm = str(c).strip().lower().replace(" ", "_").replace("-", "_")
            anorm = alias.replace(" ", "_").replace("-", "_")
            if cnorm == anorm or cnorm.endswith("_" + anorm):
                ser = pd.to_numeric(df[c], errors="coerce")
                ser.index = df["time"].values
                ser.name = "wind_speed"
                return ser
    # Fallback: any column with 'wind' and 'speed', or just 'wind' (exclude 'wind_power' etc.)
    for c in df.columns:
        c_lower = str(c).lower()
        if "wind" in c_lower and "speed" in c_lower:
            ser = pd.to_numeric(df[c], errors="coerce")
            ser.index = df["time"].values
            ser.name = "wind_speed"
            return ser
    # Last resort: column named exactly "wind" or containing "wind" (for wind speed at height)
    for c in df.columns:
        c_lower = str(c).lower()
        if c_lower == "wind" or (c_lower.startswith("wind") and "power" not in c_lower):
            ser = pd.to_numeric(df[c], errors="coerce")
            ser.index = df["time"].values
            ser.name = "wind_speed"
            return ser
    return None


def fetch_ninja_wind(
    latitude: float,
    longitude: float,
    year: int,
    capacity_kw: float,
    hub_height_m: float,
    turbine_model: str,
    include_raw: bool,
    token: str = None
) -> Dict:
    """
    Call Renewables.ninja Wind API for one year of hourly wind power data.
    
    Args:
        latitude: Site latitude (-90 to 90)
        longitude: Site longitude (-180 to 180)
        year: Year of data
        capacity_kw: Installed capacity in kW
        hub_height_m: Hub height in meters (10-300)
        turbine_model: Wind turbine model name
        include_raw: Whether to include raw weather data
        token: API authentication token (optional)
    
    Returns:
        Dict with:
            - hourly_data: pandas DataFrame
            - metadata: dict
            - annual_total_kwh: float
            - monthly_energy_kwh: List of 12 floats
    """
    
    # Use hardcoded token if none provided
    if not token:
        token = DEFAULT_NINJA_TOKEN
    
    # Validate inputs
    if not (-90 <= latitude <= 90):
        raise ValueError("Latitude must be between -90 and 90")
    if not (-180 <= longitude <= 180):
        raise ValueError("Longitude must be between -180 and 180")
    if not (10 <= hub_height_m <= 300):
        raise ValueError("Hub height must be between 10 and 300 meters")
    if capacity_kw <= 0:
        raise ValueError("Capacity must be greater than 0")
    
    # Build parameters - following API defaults
    params = {
        "lat": latitude,
        "lon": longitude,
        "date_from": f"{year}-01-01",
        "date_to": f"{year}-12-31",
        "dataset": "merra2",  # Only option for wind
        "capacity": capacity_kw,
        "height": hub_height_m,
        "turbine": turbine_model,
        "raw": "true" if include_raw else "false",
        "format": "json"
    }
    
    try:
        # Create session with auth header
        session = requests.Session()
        session.headers = {"Authorization": f"Token {token}"}
        
        # Make request
        response = session.get(WIND_ENDPOINT, params=params, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        
        # Check for API errors in response
        if "data" not in data:
            error_msg = "No data returned from Renewables.ninja"
            if "error" in data:
                error_msg = f"Ninja API error: {data['error']}"
            raise Exception(error_msg)
        
        # Parse data to DataFrame - KEEP ORIGINAL COLUMN NAMES FROM API
        df = pd.DataFrame.from_dict(data["data"], orient="index")
        
        # Parse Unix timestamps in milliseconds - KEEP as 'time' column
        try:
            df.insert(0, 'time', pd.to_datetime(df.index.astype(float), unit="ms", utc=True))
            df.reset_index(drop=True, inplace=True)
        except Exception as e:
            raise Exception(f"Error parsing timestamps: {str(e)}. Ensure data format is correct.")
        
        # Ensure we have the electricity column (Ninja returns 'electricity' in kW)
        if "electricity" not in df.columns:
            raise Exception("Unexpected API response format: no 'electricity' column found. Available columns: " + str(list(df.columns)))
        
        # Calculate annual total (electricity is in kW, hourly timestep = kWh)
        annual_kwh = float(df["electricity"].sum())
        
        # Calculate monthly totals using the datetime column
        df["_month"] = df["time"].dt.month
        
        monthly_series = df.groupby("_month")["electricity"].sum()
        
        # Build list of 12 monthly values (Jan-Dec)
        monthly_kwh = []
        for m in range(1, 13):
            monthly_kwh.append(float(monthly_series.get(m, 0.0)))
        
        # Drop the temporary _month column before returning
        df = df.drop(columns=["_month"])
        
        return {
            "hourly_data": df,
            "metadata": data.get("metadata", {}),
            "annual_total_kwh": annual_kwh,
            "monthly_energy_kwh": monthly_kwh,
            "raw_response": data
        }
        
    except requests.exceptions.Timeout:
        raise Exception("Renewables.ninja Wind API request timed out. Please try again.")
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            raise Exception("Authentication failed. Please check your API token.")
        elif response.status_code == 429:
            raise Exception("Rate limit exceeded. Please wait a moment and try again.")
        elif response.status_code == 400:
            try:
                err_data = response.json()
                err_msg = err_data.get("error", str(e))
            except:
                err_msg = str(e)
            raise Exception(f"Bad request: {err_msg}")
        else:
            raise Exception(f"HTTP error {response.status_code}: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error connecting to Renewables.ninja: {str(e)}")
    except Exception as e:
        if "Error" in str(e) and ("Parsing" in str(e) or "parsing" in str(e)):
            raise
        raise Exception(f"Error processing Ninja wind data: {str(e)}")


def fetch_ninja_pv(
    latitude: float,
    longitude: float,
    year: int,
    dataset: str,
    capacity_kw: float,
    system_loss_fraction: float,
    tracking_mode: str,   # "None", "Single-axis", "Dual-axis"
    tilt_deg: float,
    azimuth_deg: float,
    include_raw: bool,
    token: str = None
) -> Dict:
    """
    Call Renewables.ninja PV API for one year of hourly PV data.
    
    Args:
        latitude: Site latitude (-90 to 90)
        longitude: Site longitude (-180 to 180)
        year: Year of data (e.g., 2019)
        dataset: Dataset name ('merra2' or 'era5')
        capacity_kw: Installed capacity in kW
        system_loss_fraction: System losses as fraction (0-1)
        tracking_mode: Tracking type
        tilt_deg: Tilt angle in degrees
        azimuth_deg: Azimuth angle in degrees (0=South, 90=West, etc.)
        include_raw: Whether to include raw weather data
        token: API authentication token (optional, uses hardcoded default if not provided)
    
    Returns:
        Dict with:
            - hourly_data: pandas DataFrame
            - metadata: dict
            - annual_total_kwh: float
            - monthly_energy_kwh: List of 12 floats
    """
    
    # Use hardcoded token if none provided
    if not token:
        token = DEFAULT_NINJA_TOKEN
    
    # Map UI dataset labels to API values
    dataset_map = {
        "CM-SAF SARAH (Europe)": "sarah",
        "MERRA-2 (global)": "merra2"
    }
    
    dataset_key = dataset_map.get(dataset, dataset.lower().replace(" ", ""))
    if dataset_key not in ["sarah", "merra2"]:
        raise ValueError(f"Unknown dataset: {dataset}")
    
    # Map tracking mode to integer
    tracking_map = {
        "None": 0,
        "Single-axis": 1,
        "Dual-axis": 2
    }
    tracking_int = tracking_map.get(tracking_mode, 0)
    
    # Build parameters
    # Ninja API requires tilt and azimuth (unlike PVGIS which has optimal option)
    # Use provided values or defaults
    effective_tilt = tilt_deg if tilt_deg is not None else 30.0
    effective_azimuth = azimuth_deg if azimuth_deg is not None else 0.0
    
    params = {
        "lat": latitude,
        "lon": longitude,
        "date_from": f"{year}-01-01",
        "date_to": f"{year}-12-31",
        "dataset": dataset_key,
        "capacity": capacity_kw,
        "system_loss": system_loss_fraction,
        "tracking": tracking_int,
        "tilt": effective_tilt,
        "azim": effective_azimuth,
        "raw": "true" if include_raw else "false",
        "format": "json"
    }
    
    try:
        # Create session with auth header
        session = requests.Session()
        session.headers = {"Authorization": f"Token {token}"}
        
        # Make request
        response = session.get(PV_ENDPOINT, params=params, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        
        # Check for API errors in response
        if "data" not in data:
            error_msg = "No data returned from Renewables.ninja"
            if "error" in data:
                error_msg = f"Ninja API error: {data['error']}"
            raise Exception(error_msg)
        
        # Parse data to DataFrame - KEEP ORIGINAL COLUMN NAMES FROM API
        # Ninja returns data as a dict with timestamps as keys
        df = pd.DataFrame.from_dict(data["data"], orient="index")
        
        # Parse Unix timestamps in milliseconds - KEEP as 'time' column
        try:
            df.insert(0, 'time', pd.to_datetime(df.index.astype(float), unit="ms", utc=True))
            df.reset_index(drop=True, inplace=True)
        except Exception as e:
            raise Exception(f"Error parsing timestamps: {str(e)}. Ensure data format is correct.")
        
        # Ensure we have the electricity column (Ninja returns 'electricity' in kW)
        if "electricity" not in df.columns:
            raise Exception("Unexpected API response format: no 'electricity' column found. Available columns: " + str(list(df.columns)))
        
        # Calculate annual total (electricity is in kW, hourly timestep = kWh)
        annual_kwh = float(df["electricity"].sum())
        
        # Calculate monthly totals using the datetime column (not index)
        df["_month"] = df["time"].dt.month
        
        monthly_series = df.groupby("_month")["electricity"].sum()
        
        # Build list of 12 monthly values (Jan-Dec)
        monthly_kwh = []
        for m in range(1, 13):
            monthly_kwh.append(float(monthly_series.get(m, 0.0)))
        
        # Drop the temporary _month column before returning
        df = df.drop(columns=["_month"])
        
        return {
            "hourly_data": df,
            "metadata": data.get("metadata", {}),
            "annual_total_kwh": annual_kwh,
            "monthly_energy_kwh": monthly_kwh,
            "raw_response": data
        }
        
    except requests.exceptions.Timeout:
        raise Exception("Renewables.ninja API request timed out. Please try again.")
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            raise Exception("Authentication failed. Please check your API token.")
        elif response.status_code == 429:
            raise Exception("Rate limit exceeded. Please wait a moment and try again.")
        elif response.status_code == 400:
            # Try to get error message from response
            try:
                err_data = response.json()
                err_msg = err_data.get("error", str(e))
            except:
                err_msg = str(e)
            raise Exception(f"Bad request: {err_msg}")
        else:
            raise Exception(f"HTTP error {response.status_code}: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error connecting to Renewables.ninja: {str(e)}")
    except Exception as e:
        # Re-raise if it's already our formatted exception, otherwise wrap it
        if "Error" in str(e) and ("Parsing" in str(e) or "parsing" in str(e)):
            raise
        raise Exception(f"Error processing Ninja data: {str(e)}")