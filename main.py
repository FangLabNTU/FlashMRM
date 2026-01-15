#!/usr/bin/env python
# coding: utf-8

"""
Main entry point for MRM Transition Optimization Tool
"""

import argparse
import logging
import os

from config import Config
from mrm_optimizer import MRMOptimizer
from validator import InterferenceDBValidator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='MRM Transition Optimization Tool')
    parser.add_argument('--intf-db', choices=['nist', 'qe'], default='nist',
                       help='Select interference database: nist or qe (default: nist)')
    parser.add_argument('--custom-intf-db', type=str, default='',
                       help='Path to custom user-uploaded interference database (file or folder). If provided, this will be used instead of default database.')
    parser.add_argument('--max-compounds', type=int, default=375,
                       help='Maximum number of compounds to process (default: 375)')
    parser.add_argument('--output', type=str, default='optimization_results.csv',
                       help='Output filename (default: optimization_results.csv)')
    parser.add_argument('--single-compound', action='store_true',
                       help='Enable single compound input mode')
    parser.add_argument('--inchikey', type=str, default='',
                       help='Target InChIKey for single compound mode')
    parser.add_argument('--skip-validation', action='store_true',
                       help='Skip validation of custom interference database (not recommended)')
    
    args = parser.parse_args()
    
    try:
        # Create configuration
        config = Config()
        config.USE_NIST_METHOD = (args.intf_db == 'nist')
        config.MAX_COMPOUNDS = args.max_compounds
        config.OUTPUT_PATH = args.output
        config.SINGLE_COMPOUND_MODE = args.single_compound
        config.TARGET_INCHIKEY = args.inchikey
        
        # Handle custom interference database
        if args.custom_intf_db:
            custom_db_path = os.path.abspath(args.custom_intf_db)
            logger.info(f"Custom interference database detected: {custom_db_path}")
            
            # Validate custom database
            if not args.skip_validation:
                logger.info("Validating custom interference database format...")
                is_valid, error_msg = InterferenceDBValidator.validate_interference_db(
                    custom_db_path, method=args.intf_db
                )
                if not is_valid:
                    logger.error(f"Custom interference database validation failed: {error_msg}")
                    logger.error("Please check the database format, or use --skip-validation to skip validation (not recommended)")
                    return
                
                # Get database info
                db_info = InterferenceDBValidator.get_db_info(custom_db_path)
                logger.info(f"Custom interference database information:")
                logger.info(f"  Type: {db_info['type']}")
                logger.info(f"  File count: {db_info['file_count']}")
                logger.info(f"  Total rows (sampled): {db_info['total_rows']}")
            
            config.CUSTOM_INTF_DB_PATH = custom_db_path
            config.INTF_TQDB_PATH = custom_db_path
            logger.info(f"Using custom interference database: {custom_db_path}")
        else:
            # Set INTF_TQDB_PATH based on selection
            if args.intf_db == 'nist':
                config.INTF_TQDB_PATH = 'INTF_TQDB_NIST'
            else:
                config.INTF_TQDB_PATH = 'INTF_TQDB_QE'
            logger.info(f"Using default interference database: {config.INTF_TQDB_PATH}")
        
        logger.info(f"Using interference database: {config.INTF_TQDB_PATH}")
        logger.info(f"Using method: {'NIST' if config.USE_NIST_METHOD else 'QE'}")
        
        if config.SINGLE_COMPOUND_MODE:
            if not config.TARGET_INCHIKEY:
                logger.error("Single compound mode requires --inchikey parameter")
                return
            logger.info(f"Single compound mode: Target InChIKey = {config.TARGET_INCHIKEY}")
        else:
            logger.info(f"Batch mode: Processing up to {config.MAX_COMPOUNDS} compounds")
        
        # Run optimization
        optimizer = MRMOptimizer(config)
        optimizer.run_optimization()
        
    except Exception as e:
        logger.error(f"Program execution failed: {e}")
        raise


if __name__ == "__main__":
    main()
