# tests/test_preprocessing.py
import pandas as pd
import numpy as np
from src.preprocessing import DataPreprocessor

def test_parse_sentinel_values():
    # 1. Create a tiny mock dataframe with sentinel values
    mock_data = pd.DataFrame({
        'loan_type': ['Credit Card', 'Residential Mortgage'],
        'loan_to_value_pct': [-1.0, 75.0],  # -1 is sentinel for unsecured
        'property_value_change_pct_last_qtr': [-999.0, 2.5] # -999 is sentinel for non-mortgage
    })
    
    mock_rules = {
        'sentinel_values': {
            'loan_to_value_pct': -1.0,
            'property_value_change_pct_last_qtr': -999.0
        }
    }
    mock_data_config = {'paths': {'interim_data': 'data/interim/test_output.csv'}}
    
    # 2. Run the preprocessor logic
    preprocessor = DataPreprocessor(mock_rules, mock_data_config)
    processed_df = preprocessor.parse_sentinel_values(mock_data)
    
    # 3. Assertions (Verify the code did its job perfectly)
    assert processed_df.loc[0, 'loan_to_value_pct_applicable'] == 0
    assert processed_df.loc[1, 'loan_to_value_pct_applicable'] == 1
    assert np.isnan(processed_df.loc[0, 'loan_to_value_pct'])
    assert processed_df.loc[1, 'loan_to_value_pct'] == 75.0