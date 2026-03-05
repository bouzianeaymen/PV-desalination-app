import requests
import pandas as pd
from typing import Dict, Optional, Any


def fetch_pvgis_hourly(
    latitude: float,
    longitude: float,
    start_year: int,
    end_year: int,
    peak_power_kwp: float,
    system_loss_percent: float,
    mounting_type: str,  # "fixed", "inclined_axis", "two_axis"
    slope: Optional[float],
    azimuth: Optional[float],
    database: str,  # "PVGIS-ERA5", "PVGIS-SARAH3"
    optimize_slope: bool = False,
    optimize_slope_azimuth: bool = False,
    altitude: Optional[float] = None,
    pv_technology: str = "Crystalline Silicon",
    include_components: bool = False
) -> Dict[str, Any]:
    """
    Fetch hourly PV data from PVGIS API (seriescalc endpoint).
    
    Args:
        latitude: Site latitude (-90 to 90)
        longitude: Site longitude (-180 to 180)
        start_year: Start year for data (1980-2100)
        end_year: End year for data (1980-2100)
        peak_power_kwp: Installed peak power in kWp
        system_loss_percent: System losses as percentage (0-100)
        mounting_type: Mounting type ("fixed", "inclined_axis", "two_axis")
        slope: Panel slope/tilt in degrees (0-90), None for optimal
        azimuth: Panel azimuth in degrees (-180 to 180), None for optimal
        database: Solar radiation database ("PVGIS-ERA5", "PVGIS-SARAH3")
        optimize_slope: If True, use optimal tilt angle
        optimize_slope_azimuth: If True, use optimal tilt and azimuth
        altitude: Site altitude in meters (optional)
        pv_technology: PV technology type ("Crystalline Silicon", "CdTe", "CIS", "High-efficiency module")
        include_components: If True, include radiation components in output (G(d), G(b), G(i))
    
    Returns dict with:
        - hourly_data: pandas DataFrame
        - metadata: dict
        - monthly_totals: dict
        - annual_total_kwh: float
    """
    
    # Validate database (PVGIS v5.3 only supports ERA5 and SARAH3)
    VALID_DATABASES = {"PVGIS-ERA5", "PVGIS-SARAH3"}
    if database not in VALID_DATABASES:
        raise ValueError(
            f"Invalid solar radiation database '{database}'. "
            f"Choose one of: {', '.join(sorted(VALID_DATABASES))}."
        )
    
    # Validate loss percentage
    if not (0 <= system_loss_percent <= 100):
        raise ValueError("System loss must be between 0 and 100 percent")
    
    # Validate altitude if provided
    if altitude is not None and not (-9999 <= altitude <= 9999):
        raise ValueError("Altitude must be between -9999 and 9999 meters")
    
    # Map PV technology to API values
    PV_TECH_MAP = {
        "Crystalline Silicon": "crystSi",
        "CdTe": "CdTe",
        "CIS": "CIS",
        "High-efficiency module": "crystSi"  # Map to crystalline silicon
    }
    
    if pv_technology not in PV_TECH_MAP:
        raise ValueError(f"Unknown PV technology: {pv_technology}")
    
    pvtechchoice = PV_TECH_MAP[pv_technology]
    
    # Base URL for PVGIS v5.3 seriescalc (latest version)
    url = "https://re.jrc.ec.europa.eu/api/v5_3/seriescalc"
    
    # Build parameters according to PVGIS API spec
    params = {
        "lat": latitude,
        "lon": longitude,
        "startyear": start_year,
        "endyear": end_year,
        "outputformat": "json",
        "pvcalculation": 1,
        "peakpower": peak_power_kwp,
        "loss": system_loss_percent,
        "raddatabase": database,
        "pvtechchoice": pvtechchoice,
        "mountingplace": "free",
    }
    
    # Add optional altitude if provided
    if altitude is not None:
        params["alt"] = altitude
    
    # Add radiation components if requested
    if include_components:
        params["components"] = 1
    
    # Map mounting type to trackingtype
    # PVGIS tracking types:
    # 0 = fixed
    # 1 = single horizontal axis (N-S)
    # 2 = two-axis tracking  
    # 3 = vertical axis
    # 4 = single horizontal axis (E-W)
    # 5 = inclined axis (N-S)
    
    trackingtype = 0
    optimalangles = 0
    
    if mounting_type == "two_axis":
        trackingtype = 2
        # For two-axis, don't send angle/aspect
    elif mounting_type == "inclined_axis":
        trackingtype = 5  # Inclined axis tracking
        # For inclined axis, don't send fixed angle/aspect
    elif mounting_type == "vertical_axis":
        trackingtype = 3  # Vertical axis tracking
        # For vertical axis, tilt is relevant but azimuth is not (it rotates)
        # Only send tilt if provided
        if slope is not None:
            params["angle"] = slope
    else:  # "fixed"
        trackingtype = 0
        
        # Check if we have manual angle inputs
        has_manual_angles = slope is not None or azimuth is not None
        
        if optimize_slope or optimize_slope_azimuth:
            # User wants optimal angles
            optimalangles = 1
        elif has_manual_angles:
            # User provided manual angles, use them
            optimalangles = 0
            if slope is not None:
                params["angle"] = slope
            if azimuth is not None:
                params["aspect"] = azimuth
        else:
            # No angles provided and no optimization requested
            # Default to optimal angles (like PVGIS website)
            optimalangles = 1
    
    params["trackingtype"] = trackingtype
    params["optimalangles"] = optimalangles
    
    try:
        # Make request with detailed error handling
        response = requests.get(url, params=params, timeout=60)
        
        # Try to parse error message from PVGIS even on HTTP error
        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get("message", f"HTTP {response.status_code}")
            except:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            raise Exception(f"PVGIS API error: {error_msg}")
        
        response.raise_for_status()
        data = response.json()
        
        # Check for API-level errors in JSON
        if "outputs" not in data:
            error_msg = "No output data received from PVGIS"
            if "message" in data:
                error_msg = f"PVGIS Error: {data['message']}"
            raise Exception(error_msg)
        
        # Extract hourly data
        hourly_list = data.get("outputs", {}).get("hourly", [])
        
        if not hourly_list:
            raise Exception("No hourly data returned from PVGIS")
        
        # Convert to DataFrame - KEEP ORIGINAL COLUMN NAMES FROM API
        df = pd.DataFrame(hourly_list)
        
        # Calculate annual total using original column name 'P' (in Watts, hourly values)
        if 'P' in df.columns:
            annual_total_kwh = df['P'].sum() / 1000  # W to kWh
        else:
            annual_total_kwh = 0
        
        # Extract monthly totals if available
        monthly_totals = data.get("outputs", {}).get("totals", {}).get("monthly", {})
        
        return {
            "hourly_data": df,
            "metadata": data.get("inputs", {}),
            "monthly_totals": monthly_totals,
            "annual_total_kwh": annual_total_kwh,
            "raw_response": data
        }
        
    except requests.exceptions.Timeout:
        raise Exception("PVGIS API request timed out. Please try again.")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error connecting to PVGIS: {str(e)}")
    except Exception as e:
        if "PVGIS" in str(e) or "Error" in str(e):
            raise
        raise Exception(f"Error processing PVGIS data: {str(e)}")


def fetch_pvgis_tmy(
    latitude: float,
    longitude: float,
    database: str  # "PVGIS-ERA5", "PVGIS-SARAH3"
) -> Dict[str, Any]:
    """
    Fetch TMY (Typical Meteorological Year) data from PVGIS.
    
    Args:
        latitude: Site latitude (-90 to 90)
        longitude: Site longitude (-180 to 180)
        database: Solar radiation database ("PVGIS-ERA5", "PVGIS-SARAH3")
    
    Returns dict with:
        - hourly_data: pandas DataFrame
        - metadata: dict
        - months_selected: list
        - is_tmy: True
        - raw_response: dict
    """
    
    # Validate database (PVGIS v5.3 TMY only supports ERA5 and SARAH3)
    VALID_TMY_DATABASES = {"PVGIS-ERA5", "PVGIS-SARAH3"}
    if database not in VALID_TMY_DATABASES:
        raise ValueError(
            f"Invalid TMY database '{database}'. "
            f"Choose one of: {', '.join(sorted(VALID_TMY_DATABASES))}."
        )
    
    # Base URL for PVGIS v5.3 tmy (latest version)
    url = "https://re.jrc.ec.europa.eu/api/v5_3/tmy"
    
    params = {
        "lat": latitude,
        "lon": longitude,
        "raddatabase": database,
        "outputformat": "json"
    }
    
    try:
        response = requests.get(url, params=params, timeout=60)
        
        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get("message", f"HTTP {response.status_code}")
            except:
                error_msg = f"HTTP {response.status_code}"
            raise Exception(f"PVGIS TMY error: {error_msg}")
        
        response.raise_for_status()
        data = response.json()
        
        if "outputs" not in data:
            error_msg = "No output data received from PVGIS TMY"
            if "message" in data:
                error_msg = f"PVGIS Error: {data['message']}"
            raise Exception(error_msg)
        
        # TMY returns hourly data in outputs.tmy_hourly
        hourly_list = data.get("outputs", {}).get("tmy_hourly", [])
        
        if not hourly_list:
            raise Exception("No TMY hourly data returned")
            
        # Parse TMY data - KEEP ORIGINAL COLUMN NAMES INCLUDING time(UTC)
        df = pd.DataFrame(hourly_list)
        
        # Keep time(UTC) as a column (don't drop it), just parse it as datetime
        if "time(UTC)" in df.columns:
            # Parse but KEEP the original column
            df["time(UTC)"] = pd.to_datetime(df["time(UTC)"], format="%Y%m%d:%H%M", utc=True)
        
        # Keep months_selected info if available
        months_selected = data.get("outputs", {}).get("months_selected", [])
        
        return {
            "hourly_data": df,
            "metadata": data.get("inputs", {}),
            "months_selected": months_selected,
            "is_tmy": True,
            "raw_response": data
        }
        
    except requests.exceptions.Timeout:
        raise Exception("PVGIS TMY API request timed out.")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error: {str(e)}")
    except Exception as e:
        if "PVGIS" in str(e):
            raise
        raise Exception(f"Error processing TMY data: {str(e)}")