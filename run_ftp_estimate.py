from db_manager import DBManager
from ftp_estimator import FTPEstimator
import logging
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure basic logging to stdout
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    print("Initializing DB...")
    db = DBManager()
    
    estimator = FTPEstimator(db)
    
    # 0. Configuration
    # Filter for known cycling types
    cycling_types = [
        'cycling', 'road_biking', 'virtual_ride', 
        'mountain_biking', 'gravel_cycling', 'indoor_cycling'
    ]
    
    # Check for CLI args for Max HR
    known_max_hr = None
    if len(sys.argv) > 1:
        try:
            known_max_hr = int(sys.argv[1])
            print(f"User Override: Using Max HR = {known_max_hr} bpm")
        except ValueError:
            print(f"Warning: Invalid argument '{sys.argv[1]}' for Max HR. Using auto-detection.")

    print(f"Filtering for activity types: {cycling_types}")

    # 1. Advanced Field-Based Model
    print(f"\n--- Advanced Field-Based FTP Estimation ---\n")
    advanced_res = estimator.estimate_ftp_advanced(days=60, activity_types=cycling_types, known_max_hr=known_max_hr)

    if 'error' in advanced_res:
        print(f"Error: {advanced_res['error']}")
    else:
        print(f"Final Estimated FTP: {advanced_res['ftp_watts']:.1f} W")
        print(f"Confidence Score: {advanced_res.get('confidence_score', 0):.2f}")
        
        print(f"\n[Components]")
        print(f"  Model CP (Critical Power):   {advanced_res['cp_watts']:.1f} W")
        print(f"  W' (Anaerobic Capacity):     {advanced_res['w_prime']:.0f} J")
        print(f"  Best Steady-State Power:     {advanced_res['best_steady_power']:.1f} W (Duration: {advanced_res['best_steady_duration_m']:.0f} min)")
        print(f"  Aerobic Decoupling (Avg):    {advanced_res['hr_decoupling_avg']:.1f} %")

        print(f"\n[Interpretation]")
        if advanced_res['hr_decoupling_avg'] < 5.0:
            print("  - Low HR Decoupling (<5%) suggests good aerobic endurance.")
        elif advanced_res['hr_decoupling_avg'] > 8.0:
            print("  - High Decoupling (>8%) suggests potential fatigue or underdeveloped base.")
            
        diff = advanced_res['ftp_watts'] - advanced_res['best_steady_power']
        if diff < 10:
            print("  - FTP is well-anchored by real-world steady efforts.")
        else:
            print(f"  - FTP is {diff:.1f}W higher than best steady effort; ensure you can hold this power.")

    print("\n-------------------------------------------")

if __name__ == "__main__":
    main()
