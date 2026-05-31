IFRS 9 Stage 2 Migration PredictorThis repository houses a modular, production-ready machine learning framework to predict the transition of performing loans (IFRS 9 Stage 1) to a state of Significant Increase in Credit Risk (SICR) (IFRS 9 Stage 2) at the next quarterly assessment date.A Stage 2 migration triggers a shift from 12-month expected credit loss (ECL) provisioning to lifetime ECL provisioning, directly affecting a financial institution's profitability, risk-weighted assets, and regulatory capital requirements.📌 Project Overview & ObjectivesPredictive Credit Risk Modeling: Classify performing loans (Stage 1) at risk of reclassification next quarter.Sentinel Value Handling: Standardized parsing of non-applicable markers (-1, -999) across secured, unsecured, mortgage, and revolving portfolios.Early Warning Feature Engineering: Combine quantitative indicators (PD change trajectory, days past due) with qualitative indicators (payment holiday requests, overdraft breaches, forbearance history) into robust behavioral flags.XGBoost Pipeline: Train, calibrate, and serve high-performing classification models trained on class-imbalanced portfolios (~22% baseline migration rate).Stress Testing & Simulation: Evaluate portfolio risk distributions under simulated macroeconomic shock scenarios (e.g., Rising Rate environments).📂 Project Directory Structureifrs9-stage2-prediction/
├── config/                  # Configuration files (YAML format)
│   ├── business_rules.yaml  # IFRS 9 limits, thresholds, and product mapping
│   ├── data_config.yaml     # Field mappings, raw/processed pathing, data types
│   ├── model_params.yaml    # Machine learning model parameters
│   └── main_config.yaml     # Execution modes, threshold variables, and logs
├── data/                    # Structured storage for datasets (Git-ignored)
│   ├── raw/                 # Unaltered baseline portfolios (.csv) and meta files
│   ├── interim/             # Cleaned files with sentinel parsed indicators
│   └── processed/           # Feature engineered datasets ready for ML pipelines
├── models/                  # Saved serializations and training histories (.pkl)
├── notebooks/               # Step-by-step EDA and prototyping sandboxes
├── reports/                 # Output charts, evaluation metrics, and audit sheets
├── src/                     # Packaged Python codebase
│   ├── ingestion.py         # Schema-validated data loading pipeline
│   ├── preprocessing.py     # Sentinel value identifier and converter
│   ├── feature_engineering.py # Computation of behavioral indices and DPD buckets
│   ├── model_training.py    # Stratified CV-driven training logic
│   ├── model_inference.py   # Prediction score generation and staging thresholds
│   ├── report_generation.py # Visualizations and textual reporting generators
│   ├── stress_testing.py     # Shocks and macroeconomic simulations
│   ├── utils.py             # Loggers, loading utilities, and path resolvers
│   └── main.py              # Central pipeline orchestrator
├── tests/                   # Automated unit testing suite
├── requirements.txt         # Core dependencies list
└── setup.py                 # local packaging installer
⚙️ Setup and Installation1. Replicate Virtual EnvironmentUsing standard Python Virtualenv:python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
Using Conda (Anaconda/Miniconda):conda env create -f environment.yml
conda activate ifrs9-env
2. Install Project ModuleInstall the src folder as a local development package:pip install -e .
🚀 Execution Guide1. Prototype Sandbox (Development)Open the notebooks sequentially located in notebooks/:01_exploratory_data_analysis.ipynb (Review baseline portfolio dynamics and imbalanced migration distributions)02_sentinel_parsing_development.ipynb (Check validation rules for non-applicable features)03_feature_engineering_early_warning.ipynb (Design math indicators and the behavioral distress index)04_model_training_comparison.ipynb (Train models, compare metrics, and evaluate ROC-AUC outputs)05_stress_testing_simulation.ipynb (Test the portfolio against systemic shock variables)2. Running the Production Pipeline (Main)The main execution module is controlled using flags. Execute from the root directory:Train and Run Inference (Default):python -m src.main --mode train_and_predict
Train Only:python -m src.main --mode train_only
Inference/Predict Only:python -m src.main --mode predict_only
📊 IFRS 9 Framework AlignmentSICR Assessment: Evaluates whether there is a significant increase in credit risk. The primary quantitative trigger is a doubling of PD (pd_relative_change_pct > 100%) since origination.Qualitative Overrides: Integrates behavioral flags (recent forbearance events, payment holiday requests, current account unplanned debit breaches) to override purely mathematical scoring models.Backstop Rule: Classifies any asset exhibiting 30+ Days Past Due (DPD) directly into Stage 2. (Our model prioritizes early identification of assets heading into the 14-29 DPD range, exhibiting 80.2% historical migration risk).



