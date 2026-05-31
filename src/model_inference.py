# src/model_inference.py
import pandas as pd
import os
from src.utils import setup_logging, load_pickle

logger = setup_logging("ModelInference")

class InferenceEngine:
    def __init__(self, data_config: dict, main_config: dict):
        self.id_col = data_config['id_column']
        self.date_col = data_config['date_column']
        self.target = data_config['target_variable']
        self.threshold = main_config['inference_settings']['classification_threshold']
        self.model_path = "models/model_xgb.pkl"
        self.output_path = "reports/portfolio_forecasts/predicted_migration_2024Q3.csv"
        
    def run_inference(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generates probabilities and applies SICR Stage 2 classification logic."""
        logger.info(f"Running inference using threshold >= {self.threshold}")
        model = load_pickle(self.model_path)
        
        # Prepare Inference Data
        inference_data = df.drop(columns=[self.target, self.id_col, self.date_col], errors='ignore')
        
        # Predict
        probs = model.predict_proba(inference_data)[:, 1]
        
        # Create output dataframe
        results = df[[self.id_col, self.date_col]].copy() if self.id_col in df.columns else pd.DataFrame()
        results['stage_2_probability'] = probs
        results['predicted_stage'] = (probs >= self.threshold).astype(int)
        
        # Log Summary
        migrating = results['predicted_stage'].sum()
        total = len(results)
        logger.info(f"Predicted Migrations to Stage 2: {migrating} out of {total} ({migrating/total*100:.1f}%)")
        
        # Save output
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        results.to_csv(self.output_path, index=False)
        logger.info(f"Forecast saved to {self.output_path}")
        
        return results