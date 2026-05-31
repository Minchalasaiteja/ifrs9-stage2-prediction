# setup.py
from setuptools import setup, find_packages

setup(
    name="ifrs9_stage2_prediction",
    version="0.1.0",
    author="Credit Risk Modeling Team",
    description="IFRS 9 Stage 2 Migration Prediction & Stress Testing Engine",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "pandas>=1.5.0",
        "numpy>=1.22.0",
        "scikit-learn>=1.0.0",
        "xgboost>=1.6.0",
        "lightgbm>=3.3.0",
        "pyyaml>=6.0",
        "matplotlib>=3.5.0",
        "seaborn>=0.11.0",
        "openpyxl>=3.0.0",
    ],
)