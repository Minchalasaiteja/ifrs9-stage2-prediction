# src/preprocessing.py
import pandas as pd
import numpy as np
import os
from src.utils import setup_logging

logger = setup_logging("Preprocessing")

class DataPreprocessor:
    def __init__(self, business_rules: dict, data_config: dict):
        self.rules = business_rules
        self.interim_path = data_config['paths']['interim_data']
        
    def parse_sentinel_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Replaces Sentinel Values (-1, -999) with NaN so they do not skew 
        numerical averages or ML splits. Creates flags for applicability.
        """
        logger.info("Parsing sentinel values based on IFRS 9 business rules.")
        processed_df = df.copy()
        sentinels = self.rules.get('sentinel_values', {})
        
        # Parse Unsecured/Non-revolving -1 values
        for col in ['loan_to_value_pct', 'origination_ltv_pct', 'utilisation_rate_pct']:
            if col in processed_df.columns and col in sentinels:
                val = sentinels[col]
                # Create applicability flag
                processed_df[f'{col}_applicable'] = np.where(processed_df[col] == val, 0, 1)
                # Replace with NaN for modeling (XGBoost handles NaNs natively)
                processed_df[col] = processed_df[col].replace(val, np.nan)
                
        # Parse Non-mortgage -999 values
        for col in ['property_value_change_pct_last_qtr', 'ltv_change_pct_since_origination']:
            if col in processed_df.columns and col in sentinels:
                val = sentinels[col]
                processed_df[f'{col}_applicable'] = np.where(processed_df[col] == val, 0, 1)
                processed_df[col] = processed_df[col].replace(val, np.nan)
                
        return processed_df
        
    def save_interim(self, df: pd.DataFrame) -> None:
        """Saves cleaned dataset to interim path."""
        os.makedirs(os.path.dirname(self.interim_path), exist_ok=True)
        df.to_csv(self.interim_path, index=False)
        logger.info(f"Interim data saved to {self.interim_path}")