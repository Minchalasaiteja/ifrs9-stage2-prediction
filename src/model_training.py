# src/model_training.py (Updated Method Only)
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score, recall_score
import os
from src.utils import setup_logging, save_pickle

logger = setup_logging("ModelTrainer")

class ModelTrainer:
    def __init__(self, data_config: dict, model_params: dict):
        self.target = data_config['target_variable']
        self.drop_cols = [data_config['id_column'], data_config['date_column']]
        self.xgb_params = model_params.get('xgboost', {})
        self.model_save_path = "models/model_xgb.pkl"
        
    def train_xgboost(self, df: pd.DataFrame):
        """Trains the XGBoost classification model and extracts Recall."""
        logger.info("Initializing XGBoost Model Training.")
        
        if self.target not in df.columns:
            raise ValueError(f"Target '{self.target}' missing from data.")
            
        X = df.drop(columns=[self.target] + [c for c in self.drop_cols if c in df.columns])
        y = df[self.target]
        
        # Split Data (Stratified due to ~22% Stage 2 class imbalance) 
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, stratify=y, random_state=42
        )
        
        logger.info("Fitting XGBoost Classifier...")
        model = xgb.XGBClassifier(**self.xgb_params, enable_categorical=True)
        model.fit(X_train, y_train)
        
        logger.info("Evaluating on test set...")
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]
        
        # Calculate key metrics
        auc = roc_auc_score(y_test, y_prob)
        recall = recall_score(y_test, y_pred) # Captures what % of true Stage 2 migrations were caught
        
        logger.info(f"Test ROC-AUC: {auc:.4f}")
        logger.info(f"Test Recall: {recall:.4f}")
        logger.info("\n" + classification_report(y_test, y_pred))
        
        save_pickle(model, self.model_save_path)
        logger.info(f"Model saved successfully to {self.model_save_path}")
        
        return model, auc, recall  