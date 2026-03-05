"""
API Metadata Discovery Module
Fetches valid year ranges by probing API endpoints and parsing error responses
"""

import requests
import json
import re
import os
from datetime import datetime, timedelta

CACHE_FILE = "api_metadata_cache.json"
CACHE_VALIDITY_HOURS = 24  # Refresh once per day


class APIMetadataDiscovery:
    def __init__(self):
        self.cache = self._load_cache()
    
    def _load_cache(self):
        """Load cached metadata from disk"""
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r') as f:
                    data = json.load(f)
                    # Check if cache is still valid
                    cache_time = datetime.fromisoformat(data.get('timestamp', '2000-01-01'))
                    if datetime.now() - cache_time < timedelta(hours=CACHE_VALIDITY_HOURS):
                        return data.get('ranges', {})
            except Exception as e:
                print(f"Cache load failed: {e}")
        return {}
    
    def _save_cache(self, ranges):
        """Save discovered ranges to disk"""
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'ranges': ranges
            }
            with open(CACHE_FILE, 'w') as f:
                json.dump(cache_data, f)
        except Exception as e:
            print(f"Cache save failed: {e}")
    
    def _get_ninja_token(self):
        """Retrieve stored Ninja API token"""
        try:
            from .ninja_client import DEFAULT_NINJA_TOKEN
            return DEFAULT_NINJA_TOKEN
        except:
            return None
    
    def discover_pvgis_range(self, database="PVGIS-ERA5"):
        """
        Probe PVGIS API to discover valid year range
        Makes request with invalid year and parses error message
        """
        cache_key = f"pvgis_{database}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            # Probe with intentionally invalid future year
            url = "https://re.jrc.ec.europa.eu/api/v5_3/seriescalc"
            params = {
                'lat': 40.0,
                'lon': 0.0,
                'raddatabase': database,
                'peakpower': 1.0,
                'startyear': 9999,  # Invalid - will trigger error with valid range
                'endyear': 9999,
                'pvcalculation': 1,
                'outputformat': 'json'
            }
            
            response = requests.get(url, params=params, timeout=5)
            error_text = response.text
            
            if response.status_code == 400 or "error" in error_text.lower():
                # Parse PVGIS error format
                year_min, year_max = self._parse_pvgis_error_for_years(error_text)
                
                if year_min and year_max:
                    result = {"min": year_min, "max": year_max, "source": "api_probe"}
                    self.cache[cache_key] = result
                    self._save_cache(self.cache)
                    print(f"PVGIS {database} range discovered: {year_min}-{year_max}")
                    return result
            
            # Fallback to safe defaults
            return self._get_pvgis_fallback(database)
            
        except Exception as e:
            print(f"PVGIS metadata discovery failed: {e}")
            return self._get_pvgis_fallback(database)
    
    def _parse_pvgis_error_for_years(self, error_text):
        """
        Parse PVGIS error message for year ranges
        Patterns:
        - "Start year must be between 2005 and 2023"
        - "Valid years for PVGIS-ERA5 are 2005 to 2023"
        """
        patterns = [
            r'valid\s*years.*?from\s*(\d{4})\s*to\s*(\d{4})',
            r'valid\s*years.*?are\s*(\d{4})\s*to\s*(\d{4})',
            r'between\s*(\d{4})\s*and\s*(\d{4})',
            r'from\s*(\d{4})\s*to\s*(\d{4})',
            r'range\s*(\d{4})-*(\d{4})',
            r'(\d{4})\s*-\s*(\d{4})'  # Last resort: any year range
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error_text, re.IGNORECASE)
            if match:
                return int(match.group(1)), int(match.group(2))
        return None, None
    
    def _get_pvgis_fallback(self, database):
        """Fallback ranges for PVGIS databases"""
        fallbacks = {
            "PVGIS-ERA5": {"min": 2005, "max": 2023, "source": "fallback"},
            "PVGIS-SARAH3": {"min": 2005, "max": 2023, "source": "fallback"},
            "PVGIS-SARAH2": {"min": 2005, "max": 2020, "source": "fallback"},
        }
        return fallbacks.get(database, {"min": 2005, "max": 2023, "source": "fallback"})
    
    def discover_ninja_range(self, dataset_display_name):
        """
        Probe Renewables.ninja API to discover valid year range
        """
        cache_key = f"ninja_{dataset_display_name}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            # Map display names to API dataset codes
            dataset_map = {
                "CM-SAF SARAH (Europe)": "sarah",
                "MERRA-2 (global)": "merra2"
            }
            
            dataset_code = dataset_map.get(dataset_display_name, "merra2")
            token = self._get_ninja_token()
            
            if not token:
                return self._get_ninja_fallback(dataset_display_name)
            
            # Probe Ninja API with invalid date range
            url = "https://www.renewables.ninja/api/data/pv"
            params = {
                'lat': 40.0,
                'lon': 0.0,
                'dataset': dataset_code,
                'capacity': 1.0,
                'date_from': '9999-01-01',
                'date_to': '9999-12-31',
                'format': 'json'
            }
            
            headers = {'Authorization': f'Token {token}'}
            
            response = requests.get(url, params=params, headers=headers, timeout=5)
            
            if response.status_code == 400:
                try:
                    error_data = response.json()
                    error_msg = str(error_data)
                except:
                    error_msg = response.text
                
                # Parse for years
                year_min, year_max = self._parse_ninja_error_for_years(error_msg, dataset_code)
                
                if year_min and year_max:
                    result = {"min": year_min, "max": year_max, "source": "api_probe"}
                    self.cache[cache_key] = result
                    self._save_cache(self.cache)
                    print(f"Ninja {dataset_display_name} range discovered: {year_min}-{year_max}")
                    return result
            
            return self._get_ninja_fallback(dataset_display_name)
            
        except Exception as e:
            print(f"Ninja metadata discovery failed: {e}")
            return self._get_ninja_fallback(dataset_display_name)
    
    def _parse_ninja_error_for_years(self, error_msg, dataset_code):
        """Parse Ninja error message for year ranges"""
        # Find all 4-digit years in message
        # Use non-capturing group (?:19|20) to match full year, not just 19 or 20
        years = [int(y) for y in re.findall(r'\b(?:19|20)\d{2}\b', error_msg)]
        if len(years) >= 1:
            # If only one year found (e.g., max year in error), use known min
            if len(years) == 1:
                year = years[0]
                # SARAH dataset starts in 2005, MERRA-2 starts in 1980
                if 'sarah' in dataset_code.lower():
                    return 2005, year
                else:
                    return 1980, year
            return min(years), max(years)
        
        # Dataset-specific fallbacks based on known ranges
        if 'sarah' in dataset_code.lower():
            return 2005, 2015  # SARAH dataset valid range: 2005-2015
        elif 'merra2' in dataset_code.lower():
            return 1980, 2023
        return None, None
    
    def _get_ninja_fallback(self, dataset_display_name):
        """Fallback ranges for Ninja datasets"""
        fallbacks = {
            "CM-SAF SARAH (Europe)": {"min": 2005, "max": 2015, "source": "fallback"},  # SARAH: 2005-2015
            "MERRA-2 (global)": {"min": 1980, "max": 2023, "source": "fallback"},  # MERRA-2: 1980-2023
        }
        return fallbacks.get(dataset_display_name, {"min": 2000, "max": 2023, "source": "fallback"})
    
    def get_range_for_dataset(self, source_type, dataset_name):
        """
        Public method to get range with auto-discovery
        Returns: {"min": int, "max": int, "source": str}
        """
        if source_type == "pvgis":
            return self.discover_pvgis_range(dataset_name)
        elif source_type == "ninja":
            return self.discover_ninja_range(dataset_name)
        return {"min": 2000, "max": 2023, "source": "default"}
    
    def clear_cache(self):
        """Clear the cache file to force fresh discovery"""
        if os.path.exists(CACHE_FILE):
            try:
                os.remove(CACHE_FILE)
            except:
                pass
        self.cache = {}


# Global instance
metadata_discovery = APIMetadataDiscovery()
