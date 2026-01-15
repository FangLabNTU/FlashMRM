#!/usr/bin/env python
# coding: utf-8

"""
Main MRM optimizer module for MRM Transition Optimization Tool
"""

import pandas as pd
import gc
from typing import Dict, List, Optional
from tqdm import tqdm
import logging

from config import Config
from data_loader import DataLoader, LazyFileLoader
from interference_calculator import InterferenceCalculatorQE, InterferenceCalculatorNIST
from ion_optimizer import IonPairOptimizerQE, IonPairOptimizerNIST
from memory_monitor import MemoryMonitor

logger = logging.getLogger(__name__)


class MRMOptimizer:
    """Main optimizer class"""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.data_loader = DataLoader(self.config)
        
        # Initialize lazy file loader for memory-efficient queries
        self.lazy_loader = LazyFileLoader(self.config)
        
        # Initialize memory monitor
        self.memory_monitor = MemoryMonitor()
        self.memory_monitor.log_snapshot("Initialization complete")
        
        # Initialize different components based on method selection
        if self.config.USE_NIST_METHOD:
            self.interference_calc = InterferenceCalculatorNIST(self.config)
            self.ion_optimizer = IonPairOptimizerNIST(self.config, self.interference_calc)
        else:
            self.interference_calc = InterferenceCalculatorQE(self.config)
            self.ion_optimizer = IonPairOptimizerQE(self.config, self.interference_calc)
        
        # Data storage - use lazy loading mode
        self.demo_df = None
        self.pesudo_df = None  # Will not be loaded in lazy mode
        self.intf_df = None    # Will not be loaded in lazy mode
        self.matched_df = None
        self.unique_inchikeys = None  # Cache unique InChIKeys from demo_data
    
    def load_all_data(self):
        """Load all data - using lazy loading to reduce memory"""
        logger.info("Using memory-optimized mode: loading data on-demand, not loading all files at once")
        
        # In single compound mode, we don't need demo_data
        if not self.config.SINGLE_COMPOUND_MODE:
            self.demo_df = self.data_loader.load_demo_data()
            self.unique_inchikeys = self.demo_df['InChIKey'].unique().tolist()
            self.memory_monitor.log_snapshot("Demo data loaded")
            logger.info(f"Found {len(self.unique_inchikeys)} unique InChIKeys")
        else:
            # Still load demo_data but we won't use it for matching
            self.demo_df = None
            self.unique_inchikeys = None
        
        # Don't load large files - will query on-demand
        self.pesudo_df = None
        self.intf_df = None
        self.matched_df = None
        
        logger.info("Large files will be queried on-demand, memory usage will remain low")
        self.memory_monitor.log_snapshot("Data loading preparation complete")
    
    def check_inchikey_exists(self, target_inchikey: str) -> bool:
        """Check if a specific InChIKey exists"""
        # Check in demo_data first (if available)
        if self.demo_df is not None and target_inchikey in self.demo_df['InChIKey'].values:
            return True
        
        # Query on-demand from Pesudo-TQDB
        test_df = self.lazy_loader.query_by_inchikey(
            self.config.PESUDO_TQDB_PATH, target_inchikey, "Pesudo-TQDB"
        )
        return len(test_df) > 0
    
    def _save_intermediate_results(self, results: List[Dict], processed_count: int):
        """Save intermediate results"""
        if results:
            method_suffix = "nist" if self.config.USE_NIST_METHOD else "qe"
            intermediate_path = f"MRM_optimization_intermediate_{method_suffix}_{processed_count}.csv"
            result_df = pd.DataFrame(results)
            result_df.to_csv(intermediate_path, index=False, encoding='utf-8')
            logger.info(f"Intermediate results saved to {intermediate_path}")
    
    def process_compound_nist(self, inchikey: str) -> Optional[Dict]:
        """Process a single compound using NIST method"""
        logger.info(f"Processing InChIKey: {inchikey}")
        
        # Query data on-demand using lazy loader
        working_group_inchikey = self.lazy_loader.query_by_inchikey(
            self.config.PESUDO_TQDB_PATH, inchikey, "Pesudo-TQDB"
        )
        
        if len(working_group_inchikey) == 0:
            logger.warning(f"  No data found for InChIKey, skipping")
            return None
        
        # Keep only [M+H]+ type data
        working_group_inchikey = working_group_inchikey[working_group_inchikey['Precursor_type'] == '[M+H]+']
        
        if len(working_group_inchikey) == 0:
            logger.warning(f"  No [M+H]+ type data found, skipping")
            return None
        
        # Get basic information
        first_row = working_group_inchikey.iloc[0]
        precursormz = first_row['PrecursorMZ']
        rt = first_row['RT']  # Use RT
        ion_mode = first_row['Ion_mode']
        # In single compound mode, use 'Name' from pesudo_df if 'Name_x' doesn't exist
        if 'Name_x' in first_row and pd.notna(first_row['Name_x']):
            chemical = first_row['Name_x']
        elif 'Name' in first_row:
            chemical = first_row['Name']
        else:
            chemical = inchikey  # Fallback to InChIKey if no name available
        
        logger.info(f"  Compound: {chemical}")
        logger.info(f"  Precursor m/z: {precursormz}")
        logger.info(f"  RT: {rt}")
        
        # Filter fragment ions
        working_group_inchikey = working_group_inchikey[
            abs(working_group_inchikey['MSMS'] - precursormz) > self.config.PRECURSOR_MZ_MIN_DIFF
        ]
        
        if len(working_group_inchikey) < 2:
            logger.warning(f"  Insufficient available ions, skipping")
            return None
        
        # Filter and rank ions using NIST optimizer
        working_group = self.ion_optimizer.filter_and_rank_ions(working_group_inchikey)
        
        if len(working_group) < 1:
            logger.warning(f"  Insufficient ions after filtering, skipping")
            return None
        
        # Generate ion pairs using NIST optimizer
        candidate_df = self.ion_optimizer.generate_ion_pairs(working_group)
        
        if len(candidate_df) < 1:
            logger.warning(f"  No valid ion pair combinations found")
            return {
                'chemical': chemical,
                'Precursor_mz': precursormz, 
                'InChIKey': inchikey, 
                'RT': rt,
                'coverage_low': 0,
                'coverage_medium': 0,
                'coverage_high': 0,
                'coverage_all': 0,
                'best5_combinations': "no combination",
                'max_score': 0
            }
        
        # Prepare interference data - query on-demand
        different_inchikey_rows = self.lazy_loader.query_interference_by_range(
            self.config.INTF_TQDB_PATH, precursormz, rt, 0.7, self.config.RT_TOLERANCE,
            use_avg_mz=False, desc="Interference Database"
        )
        
        # Filter by ion_mode
        if len(different_inchikey_rows) > 0 and 'Ion_mode' in different_inchikey_rows.columns:
            different_inchikey_rows = different_inchikey_rows[
                different_inchikey_rows['Ion_mode'] == ion_mode
            ]
        
        different_inchikey_rows_low = different_inchikey_rows[different_inchikey_rows['NCE'] <= 60.0]
        different_inchikey_rows_medium = different_inchikey_rows[
            (different_inchikey_rows['NCE'] <= 120.0) & (different_inchikey_rows['NCE'] > 60.0)
        ]
        different_inchikey_rows_high = different_inchikey_rows[different_inchikey_rows['NCE'] > 120.0]
        
        coverage_low = len(different_inchikey_rows_low["InChIKey"].unique())
        coverage_medium = len(different_inchikey_rows_medium["InChIKey"].unique())
        coverage_high = len(different_inchikey_rows_high["InChIKey"].unique())
        coverage_all = len(different_inchikey_rows["InChIKey"].unique())
        
        logger.info(f"  Interference coverage - Low NCE: {coverage_low}, Medium NCE: {coverage_medium}, High NCE: {coverage_high}, Total: {coverage_all}")
        
        # Calculate scores using NIST optimizer
        candidate_df = self.ion_optimizer.calculate_scores(
            candidate_df, different_inchikey_rows_low, different_inchikey_rows_medium, 
            different_inchikey_rows_high, coverage_low, coverage_medium, coverage_high, coverage_all
        )
        
        # Select best ion pairs using NIST optimizer
        max_row, max10_rows = self.ion_optimizer.select_best_pairs(candidate_df)
        
        # Calculate QQQ collision energy
        if pd.notna(max_row['CE1']) and pd.notna(max_row['CE2']):
            CE1 = self.config.CE_SLOPE * float(max_row['CE1']) + self.config.CE_INTERCEPT
            CE2 = self.config.CE_SLOPE * float(max_row['CE2']) + self.config.CE_INTERCEPT
        else:
            CE1 = 0
            CE2 = 0
        
        # Add QQQ collision energy to max10_rows
        max10_rows['CE_QQQ1'] = self.config.CE_SLOPE * max10_rows['CE1'] + self.config.CE_INTERCEPT
        max10_rows['CE_QQQ2'] = self.config.CE_SLOPE * max10_rows['CE2'] + self.config.CE_INTERCEPT
        
        logger.info(f"  Best ion pair: {max_row['MSMS1']:.1f} (CE: {CE1:.1f}) / {max_row['MSMS2']:.1f} (CE: {CE2:.1f})")
        logger.info(f"  Max score: {max_row['score']:.4f}")
        logger.info(f"  Sensitivity score: {max_row['sensitivity_score']:.4f}")
        logger.info(f"  Specificity score: {max_row['specificity_score']:.4f}")
        logger.info(f"  Intensity sum: {max_row['intensity_sum']:.4f}")
        
        return {
            'chemical': chemical,
            'Precursor_mz': precursormz,
            'InChIKey': inchikey,
            'RT': rt,
            'coverage_all': coverage_all,
            'coverage_low': coverage_low,
            'coverage_medium': coverage_medium,
            'coverage_high': coverage_high,
            'MSMS1': max_row['MSMS1'],
            'MSMS2': max_row['MSMS2'],
            'CE_QQQ1': CE1,
            'CE_QQQ2': CE2,
            'best10_combinations': max10_rows.to_dict('records'),
            'max_score': max_row['score'],
            'max_sensitivity_score': max_row['sensitivity_score'],
            'max_specificity_score': max_row['specificity_score'],
            'max_intensity_sum': max_row['intensity_sum'],
        }
    
    def process_compound_qe(self, inchikey: str) -> Optional[Dict]:
        """Process a single compound using QE method"""
        logger.info(f"Processing InChIKey: {inchikey}")
        
        # Query data on-demand using lazy loader
        working_group = self.lazy_loader.query_by_inchikey(
            self.config.PESUDO_TQDB_PATH, inchikey, "Pesudo-TQDB"
        )
        
        if len(working_group) == 0:
            logger.warning(f"  No data found for InChIKey, skipping")
            return None
        
        # Keep only [M+H]+ type data
        working_group = working_group[working_group['Precursor_type'] == '[M+H]+']
        
        if len(working_group) == 0:
            logger.warning(f"  No [M+H]+ type data found, skipping")
            return None
        
        # Get basic information
        first_row = working_group.iloc[0]
        precursormz = first_row['PrecursorMZ']
        rt = first_row['RT'] + self.config.RT_OFFSET
        # In single compound mode, use 'Name' from pesudo_df if 'Name_x' doesn't exist
        if 'Name_x' in first_row and pd.notna(first_row['Name_x']):
            chemical = first_row['Name_x']
        elif 'Name' in first_row:
            chemical = first_row['Name']
        else:
            chemical = inchikey  # Fallback to InChIKey if no name available
        
        logger.info(f"  Compound: {chemical}")
        logger.info(f"  Precursor m/z: {precursormz}")
        logger.info(f"  RT: {rt}")
        
        # Filter fragment ions
        working_group = working_group[
            abs(working_group['MSMS'] - precursormz) > self.config.PRECURSOR_MZ_MIN_DIFF
        ]
        
        if len(working_group) < 2:
            logger.warning(f"  Insufficient available ions, skipping")
            return None
        
        # Filter and rank ions
        filtered_ions = self.ion_optimizer.filter_and_rank_ions(working_group)
        
        if len(filtered_ions) < 2:
            logger.warning(f"  Insufficient ions after filtering, skipping")
            return None
        
        # Generate ion pairs
        candidate_df = self.ion_optimizer.generate_ion_pairs(filtered_ions)
        
        if len(candidate_df) == 0:
            logger.warning(f"  No valid ion pair combinations found")
            return None
        
        logger.info(f"  Generated {len(candidate_df)} candidate ion pairs")
        
        # Prepare interference data
        interference_data = self.prepare_interference_data_qe(precursormz, rt)
        
        # Calculate coverage
        coverage = {
            'low': len(interference_data['low']['Alignment ID'].unique()) if len(interference_data['low']) > 0 else 0,
            'medium': len(interference_data['medium']['Alignment ID'].unique()) if len(interference_data['medium']) > 0 else 0,
            'high': len(interference_data['high']['Alignment ID'].unique()) if len(interference_data['high']) > 0 else 0,
            'all': len(interference_data['low']['Alignment ID'].unique()) + 
                   len(interference_data['medium']['Alignment ID'].unique()) + 
                   len(interference_data['high']['Alignment ID'].unique())
        }
        
        logger.info(f"  Interference coverage - Low CE: {coverage['low']}, Medium CE: {coverage['medium']}, High CE: {coverage['high']}, Total: {coverage['all']}")
        
        # Calculate scores
        candidate_df = self.ion_optimizer.calculate_scores(candidate_df, interference_data)
        
        # Select best ion pairs
        max_row, max5_rows = self.ion_optimizer.select_best_pairs(candidate_df)
        
        # Calculate QQQ collision energy
        CE1 = self.config.CE_SLOPE * float(max_row['CE1']) + self.config.CE_INTERCEPT
        CE2 = self.config.CE_SLOPE * float(max_row['CE2']) + self.config.CE_INTERCEPT
        
        # Add QQQ collision energy to max5_rows
        max5_rows['CE_QQQ1'] = self.config.CE_SLOPE * max5_rows['CE1'] + self.config.CE_INTERCEPT
        max5_rows['CE_QQQ2'] = self.config.CE_SLOPE * max5_rows['CE2'] + self.config.CE_INTERCEPT
        
        logger.info(f"  Best ion pair: {max_row['MSMS1']:.1f} (CE: {CE1:.1f}) / {max_row['MSMS2']:.1f} (CE: {CE2:.1f})")
        logger.info(f"  Max score: {max_row['score']:.4f}")
        
        return {
            'chemical': chemical,
            'Precursor_mz': precursormz,
            'InChIKey': inchikey,
            'RT': rt,
            'coverage_all': coverage['all'],
            'coverage_low': coverage['low'],
            'coverage_medium': coverage['medium'],
            'coverage_high': coverage['high'],
            'MSMS1': max_row['MSMS1'],
            'MSMS2': max_row['MSMS2'],
            'CE_QQQ1': CE1,
            'CE_QQQ2': CE2,
            'best5_combinations': max5_rows.to_dict('records'),
            'max_score': max_row['score'],
            'max_sensitivity_score': max_row['sensitivity_score'],
            'max_specificity_score': max_row['specificity_score'],
        }
    
    def prepare_interference_data_qe(self, precursormz: float, rt: float) -> Dict[str, pd.DataFrame]:
        """Prepare interference data (QE method) - query on-demand"""
        # Query interference data on-demand
        rt_filtered_rows = self.lazy_loader.query_interference_by_range(
            self.config.INTF_TQDB_PATH, precursormz, rt,
            self.config.MZ_TOLERANCE, self.config.RT_TOLERANCE,
            use_avg_mz=True, desc="Interference Database"
        )
        
        # Group by CE
        if len(rt_filtered_rows) > 0 and 'CE' in rt_filtered_rows.columns:
            interference_data = {
                'low': rt_filtered_rows[rt_filtered_rows['CE'] <= 20.0].copy(),
                'medium': rt_filtered_rows[
                    (rt_filtered_rows['CE'] > 20.0) & 
                    (rt_filtered_rows['CE'] <= 40.0)
                ].copy(),
                'high': rt_filtered_rows[rt_filtered_rows['CE'] > 40.0].copy()
            }
        else:
            interference_data = {
                'low': pd.DataFrame(),
                'medium': pd.DataFrame(),
                'high': pd.DataFrame()
            }
        
        return interference_data
    
    def run_optimization(self):
        """Run optimization"""
        method_name = "NIST" if self.config.USE_NIST_METHOD else "QE"
        logger.info(f"Starting MRM transition optimization calculation (using {method_name} method)...")
        
        # Load data
        self.load_all_data()
        
        # Initialize results table
        results = []
        
        # Handle single compound mode
        if self.config.SINGLE_COMPOUND_MODE:
            target_inchikey = self.config.TARGET_INCHIKEY.strip()
            if not target_inchikey:
                logger.error("Single compound mode enabled but no target InChIKey provided")
                return
            
            logger.info(f"Single compound mode: searching for InChIKey: {target_inchikey}")
            
            # Check if InChIKey exists
            if not self.check_inchikey_exists(target_inchikey):
                logger.warning(f"InChIKey '{target_inchikey}' not found in the database")
                # Create a not found result
                not_found_result = {
                    'chemical': 'not found',
                    'Precursor_mz': 0,
                    'InChIKey': target_inchikey,
                    'RT': 0,
                    'coverage_all': 0,
                    'coverage_low': 0,
                    'coverage_medium': 0,
                    'coverage_high': 0,
                    'MSMS1': 0,
                    'MSMS2': 0,
                    'CE_QQQ1': 0,
                    'CE_QQQ2': 0,
                    'best5_combinations': "not found",
                    'max_score': 0,
                    'max_sensitivity_score': 0,
                    'max_specificity_score': 0,
                }
                results.append(not_found_result)
                
                # Save not found result
                result_df = pd.DataFrame(results)
                result_df.to_csv(self.config.OUTPUT_PATH, index=False, encoding='utf-8')
                logger.info(f"Result saved to {self.config.OUTPUT_PATH}")
                return
            
            compounds_to_process = [target_inchikey]
            logger.info(f"Found InChIKey '{target_inchikey}', starting processing...")
        else:
            # Get unique InChIKeys to process from demo_data
            if self.unique_inchikeys is None:
                raise ValueError("unique_inchikeys not initialized. Make sure demo_data is loaded.")
            unique_inchikeys_0 = self.unique_inchikeys
            logger.info(f"Need to process {len(unique_inchikeys_0)} unique InChIKeys")
            
            # Process compounds
            compounds_to_process = unique_inchikeys_0[:self.config.MAX_COMPOUNDS] if self.config.MAX_COMPOUNDS else unique_inchikeys_0
            logger.info(f"Starting processing for {len(compounds_to_process)} compounds")
        
        processed_count = 0
        error_count = 0
        start_time = pd.Timestamp.now()
        
        for i, inchikey in enumerate(tqdm(compounds_to_process, desc='Processing compounds')):
            try:
                # Select processing function based on method
                if self.config.USE_NIST_METHOD:
                    result = self.process_compound_nist(inchikey)
                else:
                    result = self.process_compound_qe(inchikey)
                
                if result:
                    results.append(result)
                    processed_count += 1
                else:
                    error_count += 1
                
                # Monitor memory after each compound
                if (i + 1) % 5 == 0:  # Check memory every 5 compounds
                    self.memory_monitor.log_snapshot(f"After processing {i + 1} compounds")
                
                # Periodic saving of intermediate results and progress display
                if (i + 1) % self.config.SAVE_INTERVAL == 0:
                    elapsed_time = pd.Timestamp.now() - start_time
                    avg_time_per_compound = elapsed_time.total_seconds() / (i + 1)
                    remaining_compounds = len(compounds_to_process) - (i + 1)
                    estimated_remaining_time = remaining_compounds * avg_time_per_compound
                    
                    logger.info(f"Progress report:")
                    logger.info(f"  Processed: {i + 1}/{len(compounds_to_process)} compounds")
                    logger.info(f"  Successful: {processed_count}")
                    logger.info(f"  Failed/skipped: {error_count}")
                    logger.info(f"  Average time per compound: {avg_time_per_compound:.2f} seconds")
                    logger.info(f"  Estimated remaining time: {estimated_remaining_time/3600:.2f} hours")
                    logger.info(f"Saving intermediate results...")
                    self._save_intermediate_results(results, i + 1)
                    self.memory_monitor.log_snapshot("After saving intermediate results")
                
                # Periodic memory cleanup
                if (i + 1) % self.config.BATCH_SIZE == 0:
                    gc.collect()
                    self.memory_monitor.log_snapshot("After memory cleanup")
                    
            except Exception as e:
                logger.error(f"Error processing compound {inchikey}: {e}")
                error_count += 1
                continue
        
        # Final statistics
        total_time = pd.Timestamp.now() - start_time
        logger.info(f"\nProcessing completed!")
        logger.info(f"Total time: {total_time.total_seconds()/3600:.2f} hours")
        logger.info(f"Total compounds: {len(compounds_to_process)}")
        logger.info(f"Successfully processed: {processed_count}")
        logger.info(f"Failed/skipped: {error_count}")
        logger.info(f"Success rate: {processed_count/len(compounds_to_process)*100:.1f}%")
        
        # Final memory snapshot
        self.memory_monitor.log_snapshot("Processing complete")
        
        # Save results
        if results:
            result_df = pd.DataFrame(results)
            result_df.to_csv(self.config.OUTPUT_PATH, index=False, encoding='utf-8')
            logger.info(f"Final results saved to {self.config.OUTPUT_PATH}")
            self.memory_monitor.log_snapshot("After saving final results")
            
            # Display results summary
            logger.info("\nResults summary:")
            summary_columns = ['chemical', 'MSMS1', 'MSMS2', 'CE_QQQ1', 'CE_QQQ2', 'max_score', 'max_sensitivity_score', 'max_specificity_score']
            available_columns = [col for col in summary_columns if col in result_df.columns]
            print(result_df[available_columns].head(10))
        else:
            logger.warning("No compounds processed successfully")
        
        # Display memory usage summary
        summary = self.memory_monitor.get_summary()
        logger.info("\n" + "="*60)
        logger.info("Memory Usage Summary:")
        logger.info("="*60)
        logger.info(f"Maximum memory usage: {summary['max_memory_mb']:.2f} MB ({summary['max_memory_gb']:.3f} GB)")
        logger.info(f"Exceeds 2GB limit: {'Yes' if summary['max_memory_gb'] > 2.0 else 'No'}")
        logger.info("\nMemory usage at key points:")
        for snapshot in summary['snapshots']:
            logger.info(f"  {snapshot['label']}: Peak={snapshot['peak_mb']:.2f} MB")
        logger.info("="*60)
