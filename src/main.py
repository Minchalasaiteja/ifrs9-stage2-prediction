# src/main.py
import argparse
from src.utils import setup_logging, load_yaml_config
from src.ingestion import DataLoader
from src.preprocessing import DataPreprocessor
from src.feature_engineering import FeatureEngineer
from src.model_training import ModelTrainer
from src.model_inference import InferenceEngine
from src.stress_testing import StressTester
from src.report_generation import generate_summary_report

logger = setup_logging("MainPipeline")

def run_pipeline(mode: str):
    # Load Configs
    logger.info("Loading Configurations...")
    main_config = load_yaml_config('config/main_config.yaml')
    data_config = load_yaml_config('config/data_config.yaml')
    biz_rules = load_yaml_config('config/business_rules.yaml')
    model_params = load_yaml_config('config/model_params.yaml')

    # 1. Ingest
    loader = DataLoader(data_config)
    raw_df = loader.load_raw_data()
    
    # 2. Preprocess
    if main_config['pipeline_flags']['run_preprocessing']:
        preprocessor = DataPreprocessor(biz_rules, data_config)
        clean_df = preprocessor.parse_sentinel_values(raw_df)
        preprocessor.save_interim(clean_df)
    else:
        clean_df = raw_df # fallback
        
    # 3. Feature Engineer
    if main_config['pipeline_flags']['run_feature_engineering']:
        engineer = FeatureEngineer(data_config)
        features_df = engineer.engineer_early_warning_signals(clean_df)
        engineer.save_features(features_df)
    else:
        features_df = clean_df

    # 4. Train
    if mode in ['train_and_predict', 'train_only']:
        if main_config['pipeline_flags']['train_models']:
            trainer = ModelTrainer(data_config, model_params)
            model, auc, recall = trainer.train_xgboost(features_df)
            
            # 5. Reporting
            if main_config['pipeline_flags']['generate_reports']:
                generate_summary_report({'Model': 'XGBoost', 'Test ROC-AUC': auc})

    # 6. Predict / Inference
    if mode in ['train_and_predict', 'predict_only']:
        inference = InferenceEngine(data_config, main_config)
        results = inference.run_inference(features_df)
        
        # Optional Stress Testing
        stress_tester = StressTester(inference)
        logger.info("Running Baseline vs Stress Comparison...")
        stress_tester.simulate_macro_shock(features_df, 'Rising_Rates')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IFRS 9 Stage 2 Prediction Pipeline")
    parser.add_argument("--mode", type=str, default="train_and_predict", 
                        choices=["train_and_predict", "train_only", "predict_only"],
                        help="Execution mode for the pipeline.")
    args = parser.parse_args()
    
    logger.info(f"Starting IFRS 9 Pipeline in mode: {args.mode}")
    try:
        run_pipeline(args.mode)
        logger.info("Pipeline executed successfully.")
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}", exc_info=True)