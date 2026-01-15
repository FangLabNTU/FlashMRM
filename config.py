#!/usr/bin/env python
# coding: utf-8

"""
Configuration module for MRM Transition Optimization Tool
"""

from dataclasses import dataclass


@dataclass
class Config:
    """Configuration class to centralize all parameters"""
    # Data file paths
    DEMO_DATA_PATH: str = '375pesticides_inchikey.csv'
    PESUDO_TQDB_PATH: str = 'Pesudo-TQDB'  # Folder path
    INTF_TQDB_PATH: str = 'INTF_TQDB_NIST'  # Folder path, default to NIST data
    CUSTOM_INTF_DB_PATH: str = ""  # Custom user-uploaded interference database path
    OUTPUT_PATH: str = 'optimization_results.csv'
    
    # Processing parameters
    CHUNK_SIZE: int = 100000
    MAX_COMPOUNDS: int = 375  # Process all compounds, None means process all
    MZ_TOLERANCE: float = 0.7
    RT_TOLERANCE: float = 2.0  # 2 minutes tolerance (RT converted to minutes)
    MSMS_TOLERANCE: float = 0.7
    PRECURSOR_MZ_MIN_DIFF: float = 14.0126
    ION_PAIR_MIN_DIFF: float = 2.0
    MAX_IONS_PER_CE: int = 10
    RT_OFFSET: float = 0.0  # Do not use RT offset
    
    # Batch processing parameters
    BATCH_SIZE: int = 50  # Number of compounds processed per batch
    SAVE_INTERVAL: int = 100  # Save intermediate results after processing this many compounds
    
    # Scoring parameters
    SENSITIVITY_WEIGHT: float = 0.5
    SPECIFICITY_WEIGHT: float = 0.5
    
    # QQQ conversion parameters
    CE_SLOPE: float = 0.5788
    CE_INTERCEPT: float = 9.4452
    
    # Interference calculation method selection
    USE_NIST_METHOD: bool = True  # True uses NIST method, False uses QE method
    
    # Input mode selection
    SINGLE_COMPOUND_MODE: bool = False  # True for single compound input mode
    TARGET_INCHIKEY: str = ""  # Target InChIKey for single compound mode
