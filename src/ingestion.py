# src/ingestion.py
import pandas as pd
import os
from src.utils import setup_logging

logger = setup_logging("Ingestion")

class DataLoader:
    def __init__(self, data_config: dict):
        self.raw_path = data_config['paths']['raw_data']
        self.expected_target = data_config['target_variable']
        
    def load_raw_data(self) -> pd.DataFrame:
        """Loads raw portfolio data from CSV and validates schema presence."""
        logger.info(f"Loading raw data from: {self.raw_path}")
        if not os.path.exists(self.raw_path):
            raise FileNotFoundError(f"Raw data file missing at {self.raw_path}")
            
        df = pd.read_csv(self.raw_path)
        logger.info(f"Loaded {df.shape[0]} rows and {df.shape[1]} columns.")
        
        if self.expected_target not in df.columns:
            logger.warning(f"Target variable '{self.expected_target}' not found. Ensure this is inference data.")
            
        return df