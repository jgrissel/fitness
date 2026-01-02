import pandas as pd
import logging

logger = logging.getLogger(__name__)

def parse_activity_details(details_json):
    """
    Parses the raw JSON details from Garmin into a Pandas DataFrame.
    
    Args:
        details_json (dict): The dictionary containing 'metricDescriptors' and 'activityDetailMetrics'.
        
    Returns:
        pd.DataFrame: A DataFrame with columns named after the metric keys (e.g., 'directHeartRate', 'directTimestamp').
    """
    try:
        if not details_json or 'metricDescriptors' not in details_json or 'activityDetailMetrics' not in details_json:
            return pd.DataFrame()

        # 1. Map Usage Indices to Keys
        # Descriptors look like: { "metricsIndex": 0, "key": "directHeartRate", ... }
        descriptors = details_json['metricDescriptors']
        index_to_key = {}
        for desc in descriptors:
            idx = desc.get('metricsIndex')
            key = desc.get('key')
            if idx is not None and key:
                index_to_key[idx] = key

        # 2. Extract Data
        # Metrics look like: { "metrics": [123, 456, ...] }
        # The list is sparse/ordered by index. 
        # CAUTION: The 'metrics' array in 'activityDetailMetrics' corresponds to the 'metricDescriptors' 
        # BUT they might not be strictly positional if the descriptor indices are effectively IDs.
        # However, usually Garmin's 'metrics' array is ordered matching the descriptors list order OR 
        # more commonly, the descriptor's 'metricsIndex' tells you which slot in the 'metrics' array refers to that key.
        # Let's verify: In the dump, metricDescriptors has indices 0 to 13.
        # The data 'metrics' array has 14 elements. So it maps directly by index.
        
        data_rows = []
        for entry in details_json['activityDetailMetrics']:
            row = {}
            values = entry.get('metrics', [])
            
            for i, val in enumerate(values):
                # 'i' here is the position in the list.
                # We assume this corresponds to 'metricsIndex' == i.
                if i in index_to_key:
                    row[index_to_key[i]] = val
            
            data_rows.append(row)

        df = pd.DataFrame(data_rows)
        
        # 3. Post-Processing / Cleanup
        # Convert timestamp (usually 'directTimestamp') to datetime
        if 'directTimestamp' in df.columns:
            # Garmin often uses epoch millis or similar. Let's check the units in descriptor if needed.
            # In the dump: key: "gmt", factor: 0.0. Wait, factor 0.0?
            # Looking at sample: 1766943593000.0 -> This looks like ms epoch? 
            # 1766943593000 / 1000 = 1766943593 -> Year 2025 (roughly). Matches current date.
            df['timestamp'] = pd.to_datetime(df['directTimestamp'], unit='ms')
            
        # Rename common columns for friendlier access
        # Rename common columns for friendlier access
        column_map = {
            'directHeartRate': 'heart_rate',
            'directSpeed': 'speed',
            'directElevation': 'elevation',
            'directLatitude': 'latitude',
            'directLongitude': 'longitude',
            'sumDistance': 'distance',
            # 'directTimestamp': 'timestamp', # Handled manually above
            
            # Power
            'directPower': 'power',
            
            # Cadence variations
            'directCadence': 'cadence',
            'directRunCadence': 'cadence',
            'directBikeCadence': 'cadence',
            'directRunningCadence': 'cadence',
            'directCyclingCadence': 'cadence',
            'directSwimCadence': 'cadence'
        }
        df.rename(columns=column_map, inplace=True)
        
        return df

    except Exception as e:
        logger.error(f"Error parsing activity details: {e}")
        return pd.DataFrame()

def calculate_normalized_power(power_series: pd.Series, window: int = 30) -> float:
    """
    Calculate Normalized Power (NP) for a series of power data.
    NP = (mean(rolling_avg_30s^4))^0.25
    """
    if power_series.empty:
        return 0.0
        
    # 1. Rolling 30s average
    rolling_avg = power_series.rolling(window=window).mean()
    
    # 2. Raise to 4th power
    rolling_pow4 = rolling_avg ** 4
    
    # 3. Average of the values
    avg_pow4 = rolling_pow4.mean()
    
    # 4. Fourth root
    if avg_pow4 > 0:
        return float(avg_pow4 ** 0.25)
    return 0.0

def calculate_decoupling(df: pd.DataFrame) -> float:
    """
    Calculate Aerobic Decoupling (Pa:HR).
    Compares Efficiency Factor (NP/HR) of the first half vs second half.
    Returns percentage increase in HR relative to Power (or drop in efficiency).
    Decoupling = (EF1 - EF2) / EF1 * 100
    Where EF = Normalized Power / Average Heart Rate
    """
    if df.empty or 'power' not in df.columns or 'heart_rate' not in df.columns:
        return 0.0
        
    midpoint = len(df) // 2
    first_half = df.iloc[:midpoint]
    second_half = df.iloc[midpoint:]
    
    # Calculate Efficiency Factor (EF) for each half
    # EF = NP / Avg HR
    def get_ef(segment):
        if segment.empty: return 0.0
        np_val = calculate_normalized_power(segment['power'])
        avg_hr = segment['heart_rate'].mean()
        if avg_hr and avg_hr > 0:
            return np_val / avg_hr
        return 0.0
        
    ef1 = get_ef(first_half)
    ef2 = get_ef(second_half)
    
    if ef1 > 0:
        return (ef1 - ef2) / ef1 * 100.0
    return 0.0

