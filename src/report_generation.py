# src/report_generation.py
import pandas as pd
import os
from src.utils import setup_logging

logger = setup_logging("Reporting")

def generate_summary_report(metrics: dict, output_dir: str = "reports/metrics"):
    """Saves validation metrics and final portfolio statistics to text summaries."""
    logger.info("Generating Summary Reports...")
    os.makedirs(output_dir, exist_ok=True)
    
    filepath = os.path.join(output_dir, "validation_summary.txt")
    with open(filepath, "w") as f:
        f.write("=== IFRS 9 STAGE 2 PREDICTION SUMMARY ===\n")
        for key, value in metrics.items():
            f.write(f"{key}: {value}\n")
            
    logger.info(f"Metrics saved to {filepath}")
    # Note: Full PDF/Visual generation would use matplotlib/seaborn here.