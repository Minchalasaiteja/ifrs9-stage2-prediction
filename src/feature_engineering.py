# src/feature_engineering.py
import pandas as pd
import numpy as np
import os
from src.utils import setup_logging

logger = setup_logging("FeatureEngineering")

class FeatureEngineer:
    def __init__(self, data_config: dict):
        self.processed_path = data_config['paths']['processed_data']
        self.cat_cols = data_config['schema']['categorical_features']
        
    def engineer_early_warning_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculates DPD buckets and behavioral distress signals."""
        logger.info("Engineering early-warning risk features.")
        feat_df = df.copy()
        
        # 1. DPD Bucketing
        if 'days_past_due_current' in feat_df.columns:
            bins = [-1, 0, 6, 13, 29, 999]
            labels = ['0_DPD', '1-6_DPD', '7-13_DPD', '14-29_DPD', '30+_DPD']
            feat_df['dpd_bucket'] = pd.cut(feat_df['days_past_due_current'], bins=bins, labels=labels)
            
        # 2. Behavioral Distress Score (Composite Index)
        feat_df['behavioral_distress_score'] = 0
        if 'payment_reduction_requested' in feat_df.columns:
            feat_df['behavioral_distress_score'] += np.where(feat_df['payment_reduction_requested'] == 'Yes', 3, 0)
        if 'forbearance_history' in feat_df.columns:
            feat_df['behavioral_distress_score'] += np.where(feat_df['forbearance_history'] == 'Yes', 2, 0)
        if 'current_account_debit_flag' in feat_df.columns:
            feat_df['behavioral_distress_score'] += np.where(feat_df['current_account_debit_flag'] == 'Yes', 2, 0)
        if 'missed_payments_last_12m' in feat_df.columns:
            feat_df['behavioral_distress_score'] += feat_df['missed_payments_last_12m']
            
        # 3. Format Categorical Variables for XGBoost (Convert to 'category' dtype)
        for col in self.cat_cols + ['dpd_bucket']:
            if col in feat_df.columns:
                feat_df[col] = feat_df[col].astype('category')
                
        return feat_df
        
    def save_features(self, df: pd.DataFrame) -> None:
        """Saves ML-ready features to processed directory."""
        os.makedirs(os.path.dirname(self.processed_path), exist_ok=True)
        df.to_csv(self.processed_path, index=False)
        logger.info(f"Feature-engineered data saved to {self.processed_path}")