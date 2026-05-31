# src/utils.py
import os
import yaml
import logging
import pickle

def setup_logging(name: str, log_level: str = "INFO") -> logging.Logger:
    """Sets up standard logging for the pipeline."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        ch = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    return logger

def load_yaml_config(filepath: str) -> dict:
    """Loads a YAML configuration file."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Configuration file not found: {filepath}")
    with open(filepath, 'r') as file:
        return yaml.safe_load(file)

def save_pickle(obj: any, filepath: str) -> None:
    """Serializes an object to a pickle file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'wb') as f:
        pickle.dump(obj, f)

def load_pickle(filepath: str) -> any:
    """Loads a serialized object from a pickle file."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Pickle file not found: {filepath}")
    with open(filepath, 'rb') as f:
        return pickle.load(f)