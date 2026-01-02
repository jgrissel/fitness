import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from db_manager import DBManager
from activity_parser import parse_activity_details, calculate_normalized_power, calculate_decoupling

logger = logging.getLogger(__name__)

class FTPEstimator:
    def __init__(self, db_manager: DBManager):
        self.db = db_manager
        # Durations for MMP Curve (in seconds)
        # 3m, 5m, 10m, 20m, 30m, 40m, 60m
        self.mmp_durations = [180, 300, 600, 1200, 1800, 2400, 3600] 
    
    def calculate_rolling_max_power(self, df: pd.DataFrame, duration_seconds: int) -> float:
        """Calculate the maximum rolling average power for a given duration."""
        if 'power' not in df.columns or df.empty:
            return 0.0
        
        # Ensure numeric
        series = pd.to_numeric(df['power'], errors='coerce').fillna(0)
        
        if len(series) < duration_seconds:
            return 0.0
            
        rolling_mean = series.rolling(window=duration_seconds).mean()
        return rolling_mean.max()

    def get_season_best_curve(self, days: int = 60, activity_types: List[str] = None) -> Tuple[Dict[int, float], Dict[int, int]]:
        """
        Step 1: Build Maximal Mean Power (MMP) Curve
        """
        activity_ids = self.db.get_recent_activity_ids(days, activity_types=activity_types)
        
        best_powers = {d: 0.0 for d in self.mmp_durations}
        contributing_activities = {d: None for d in self.mmp_durations}
        
        logger.info(f"Analyzing {len(activity_ids)} activities for MMP curve...")
        
        for activity_id in activity_ids:
            details = self.db.get_activity_details_json(activity_id)
            if not details: continue
            df = parse_activity_details(details)
            if df.empty or 'power' not in df.columns: continue
            
            for duration in self.mmp_durations:
                val = self.calculate_rolling_max_power(df, duration)
                if val > best_powers[duration]:
                    best_powers[duration] = val
                    contributing_activities[duration] = activity_id
                    
        return best_powers, contributing_activities

    def fit_cp_model(self, mmp_curve: Dict[int, float]) -> Dict:
        """
        Step 2: Fit Power-Duration Model (2-parameter CP)
        Using durations >= 3 mins (180s)
        Formula: Work = CP * t + W'
        """
        valid_points = [(t, p) for t, p in mmp_curve.items() if p > 0 and t >= 180]
        
        if len(valid_points) < 2:
            return {'error': "Not enough valid data points (>= 3 mins)"}
            
        X = np.array([p[0] for p in valid_points]) # Time
        Powers = np.array([p[1] for p in valid_points])
        Y = Powers * X # Work
        
        # Regression Y = CP*X + W'
        A = np.vstack([X, np.ones(len(X))]).T
        cp, w_prime = np.linalg.lstsq(A, Y, rcond=None)[0]
        
        return {'cp': cp, 'w_prime': w_prime}

    def find_best_steady_state(self, days: int = 60, activity_types: List[str] = None) -> Dict:
        """
        Step 4: Best Steady-State Power Check
        Find best effort: 40-70 min, VI <= 1.05
        """
        activity_ids = self.db.get_recent_activity_ids(days, activity_types=activity_types)
        best_steady = {'power': 0.0, 'duration': 0, 'activity_id': None, 'vi': 0.0}
        
        for activity_id in activity_ids:
            details = self.db.get_activity_details_json(activity_id)
            if not details: continue
            df = parse_activity_details(details)
            if df.empty or 'power' not in df.columns: continue
            
            # We want to find the best 40-70 minute segment
            # Optimization: Just look at fixed windows e.g. 40m, 50m, 60m maxes?
            # Or sliding window? Computationally expensive.
            # Simplified: Check the Whole Ride if Duration is in range?
            # Spec says "Identify best continuous effort".
            # Let's check 40m and 60m rolling maxes.
            
            for duration in [2400, 3600]: # 40m, 60m
                if len(df) < duration: continue
                
                # Rolling Avg Power
                rolling_p = df['power'].rolling(window=duration).mean()
                # Rolling NP? Calculating NP for every window is wildly expensive (O(N*M))
                # Heuristic: 
                # 1. Find time of Max Avg Power
                idx_end = rolling_p.idxmax()
                max_avg_p = rolling_p.max()
                
                if pd.isna(idx_end): continue
                
                # 2. Extract that segment
                idx_start = idx_end - duration + 1
                segment = df.iloc[int(idx_start):int(idx_end)+1]
                
                # 3. Calculate NP & VI for that segment
                np_val = calculate_normalized_power(segment['power'])
                vi = np_val / max_avg_p if max_avg_p > 0 else 999
                
                if vi <= 1.05:
                    if max_avg_p > best_steady['power']:
                        best_steady = {
                            'power': max_avg_p, 
                            'duration': duration, 
                            'activity_id': activity_id,
                            'vi': vi
                        }
        
        return best_steady

    def get_avg_decoupling(self, days: int = 60, activity_types: List[str] = None) -> float:
        """
        Step 5: HR-Power Decoupling Validation
        Avg decoupling for long rides (> 60m)
        """
        activity_ids = self.db.get_recent_activity_ids(days, activity_types=activity_types)
        decouplings = []
        
        for activity_id in activity_ids:
            details = self.db.get_activity_details_json(activity_id)
            if not details: continue
            df = parse_activity_details(details)
            if len(df) < 3600: continue # Skip short rides
            
            d = calculate_decoupling(df)
            # Filter sane values (-20% to +30%)
            if -20 < d < 30: 
                decouplings.append(d)
                
        if not decouplings: return 0.0
        return sum(decouplings) / len(decouplings)

    def estimate_ftp_advanced(self, days: int = 60, activity_types: List[str] = None) -> Dict:
        """
        Execute Advanced Field-Based FTP Estimation (5-Step Logic)
        """
        # Step 1: MMP Curve
        mmp_curve, _ = self.get_season_best_curve(days, activity_types)
        
        # Step 2: Fit CP Model
        cp_result = self.fit_cp_model(mmp_curve)
        if 'error' in cp_result:
            return cp_result
            
        cp_ftp = cp_result['cp']
        
        # Step 3: Modeled FTP & Initial Clamp help
        # "Clamp: FTP must be within 10% of best observed 40-70 min power"
        # We need the best steady state for this clamping (Step 4)
        
        # Step 4: Best Steady-State
        steady_res = self.find_best_steady_state(days, activity_types)
        best_steady_p = steady_res['power']
        
        ftp_modeled = cp_ftp
        
        # Clamp logic: if Model is way higher than what we've actually done for 40m
        # But only if we HAVE a 40m effort.
        if best_steady_p > 0:
            upper_bound = best_steady_p * 1.15 # looser clamp? Spec says 10%? 
            # "FTP must be within 10% of best observed 40-70 min power unless overridden"
            # If CP > 1.10 * Steady, clamp it down?
            # Or if CP < 0.90 * Steady (unlikely), clamp it up?
            
            if ftp_modeled > (best_steady_p * 1.10):
                logger.info(f"Clamping FTP down: CP ({ftp_modeled:.1f}) > 1.1 * Steady ({best_steady_p:.1f})")
                ftp_modeled = best_steady_p * 1.10
                
        # "If FTP_modeled > best_steady_power * 1.05 -> reduce FTP toward steady-state value"
        # This seems to duplicate the clamp but suggests a soft reduction.
        
        # Step 5: Decoupling
        decoupling = self.get_avg_decoupling(days, activity_types)
        
        # confidence modifier?
        # "<5% -> FTP likely valid"
        # "7-8% -> FTP likely too high"
        
        # Step 6: Final Weighting
        # "FTP_final = weighted_mean(FTP_modeled (70%), best_steady_power (30%))"
        # If best_steady_p is 0 (no long rides), we rely 100% on CP
        
        if best_steady_p > 0:
            final_ftp = (0.7 * ftp_modeled) + (0.3 * best_steady_p)
            
            # "Adjust weighting if HR decoupling flags instability."
            if decoupling > 7.0:
                # Fatigue present, trust steady state more? or reduce estimate?
                # Let's shift weight to Steady Power (real performance) vs Model (potential)
                final_ftp = (0.5 * ftp_modeled) + (0.5 * best_steady_p)
        else:
            final_ftp = ftp_modeled
            
        return {
            "ftp_watts": float(final_ftp),
            "confidence_score": 0.8 if decoupling < 5 else 0.5, # Simplified
            "cp_watts": float(cp_ftp),
            "w_prime": float(cp_result['w_prime']),
            "best_steady_power": float(best_steady_p),
            "best_steady_duration_m": steady_res['duration'] / 60,
            "hr_decoupling_avg": float(decoupling),
            "data_coverage_days": days
        }
