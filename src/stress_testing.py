# src/stress_testing.py
import pandas as pd
from src.utils import setup_logging

logger = setup_logging("StressTesting")

class StressTester:
    def __init__(self, inference_engine):
        self.engine = inference_engine
        
    def simulate_macro_shock(self, df: pd.DataFrame, shock_type: str = 'Rising_Rates') -> pd.DataFrame:
        """Modifies portfolio parameters to simulate macroeconomic stress safely."""
        logger.info(f"Initiating Stress Test Simulation: {shock_type}")
        stress_df = df.copy()
        
        if shock_type == 'Rising_Rates':
            if 'interest_rate_environment' in stress_df.columns:
                # 1. Force the entire portfolio into a rising rate environment
                stress_df['interest_rate_environment'] = 'Rising'
                
                # 2. Safely cast it back to a category type so XGBoost doesn't reject it
                stress_df['interest_rate_environment'] = stress_df['interest_rate_environment'].astype('category')
                
                # 3. Simulate a slight bump in days past due for vulnerable segments
                if 'days_past_due_current' in stress_df.columns:
                    stress_df['days_past_due_current'] += 2
                    
        # 4. PLACE HERE: Alter the output file path destination dynamically 
        # so this simulation run doesn't overwrite your baseline calculations.
        self.engine.output_path = "reports/portfolio_forecasts/predicted_stress_migration_2024Q3.csv"
                    
        # Re-run inference with the corrected categorical data type
        results = self.engine.run_inference(stress_df)
        logger.info(f"Stress Test '{shock_type}' complete.")
        return results