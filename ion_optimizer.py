#!/usr/bin/env python
# coding: utf-8

"""
Ion pair optimization module for MRM Transition Optimization Tool
"""

import pandas as pd
import numpy as np
from itertools import combinations
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class IonPairOptimizerQE:
    """Ion pair optimizer for QE method"""
    
    def __init__(self, config, interference_calc):
        self.config = config
        self.interference_calc = interference_calc
    
    def filter_and_rank_ions(self, working_group: pd.DataFrame) -> pd.DataFrame:
        """Filter and rank ions"""
        # Group by CE
        ce_groups = {
            'low': working_group[working_group['CE'] <= 20.0],
            'medium': working_group[
                (working_group['CE'] > 20.0) & 
                (working_group['CE'] <= 40.0)
            ],
            'high': working_group[working_group['CE'] > 40.0]
        }
        
        # Determine which name column to use
        name_col = 'Name_x' if 'Name_x' in working_group.columns else 'Name'
        
        filtered_ions = []
        
        for ce_level, group in ce_groups.items():
            if len(group) > 0:
                # Sort by intensity
                group_sorted = group.sort_values('intensity', ascending=False)
                # Deduplicate
                group_dedup = group_sorted.drop_duplicates([name_col, 'MSMS'], keep='first')
                # Take top N
                group_filtered = group_dedup.head(self.config.MAX_IONS_PER_CE)
                filtered_ions.append(group_filtered)
        
        return pd.concat(filtered_ions, ignore_index=True) if filtered_ions else pd.DataFrame()
    
    def generate_ion_pairs(self, ions_df: pd.DataFrame) -> pd.DataFrame:
        """Generate ion pair combinations"""
        if len(ions_df) < 2:
            return pd.DataFrame()
        
        combinations_list = list(combinations(ions_df.iterrows(), 2))
        candidate_data = []
        
        for (index1, row1), (index2, row2) in combinations_list:
            if (row1['MSMS'] != row2['MSMS'] and 
                abs(row1['MSMS'] - row2['MSMS']) >= self.config.ION_PAIR_MIN_DIFF):
                candidate_data.append([
                    row1['MSMS'], row1['intensity'], row1['CE'],
                    row2['MSMS'], row2['intensity'], row2['CE']
                ])
        
        if not candidate_data:
            return pd.DataFrame()
        
        candidate_df = pd.DataFrame(candidate_data, columns=[
            'MSMS1', 'intensity1', 'CE1', 'MSMS2', 'intensity2', 'CE2'
        ])
        
        return candidate_df
    
    def calculate_scores(self, 
                        candidate_df: pd.DataFrame, 
                        interference_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Calculate scores"""
        # Calculate interference levels
        target_ions_1 = candidate_df['MSMS1'].values
        target_ions_2 = candidate_df['MSMS2'].values
        
        interference_levels_1 = np.zeros(len(candidate_df))
        interference_levels_2 = np.zeros(len(candidate_df))
        
        for index, row in candidate_df.iterrows():
            ce1 = row['CE1']
            ce2 = row['CE2']
            
            # Select interference data based on CE
            if ce1 <= 20.0:
                intf_data_1 = interference_data['low']
            elif ce1 <= 40.0:
                intf_data_1 = interference_data['medium']
            else:
                intf_data_1 = interference_data['high']
            
            if ce2 <= 20.0:
                intf_data_2 = interference_data['low']
            elif ce2 <= 40.0:
                intf_data_2 = interference_data['medium']
            else:
                intf_data_2 = interference_data['high']
            
            # Calculate interference levels
            interference_levels_1[index] = sum(
                self.interference_calc.extract_intensity_from_msms_cached(
                    intf_row['MS/MS spectrum'], row['MSMS1']
                ) for _, intf_row in intf_data_1.iterrows()
            )
            
            interference_levels_2[index] = sum(
                self.interference_calc.extract_intensity_from_msms_cached(
                    intf_row['MS/MS spectrum'], row['MSMS2']
                ) for _, intf_row in intf_data_2.iterrows()
            )
        
        candidate_df['interference_level1'] = interference_levels_1
        candidate_df['interference_level2'] = interference_levels_2
        candidate_df['intensity_sum'] = candidate_df['intensity1'] + candidate_df['intensity2']
        candidate_df['interference_level_sum'] = interference_levels_1 + interference_levels_2
        
        # Calculate scores
        max_intensity = candidate_df['intensity_sum'].max()
        max_interference = candidate_df['interference_level_sum'].max()
        
        if max_intensity > 0 and max_interference > 0:
            # Calculate scoring metrics
            candidate_df['sensitivity_score'] = candidate_df['intensity_sum'] / max_intensity
            candidate_df['specificity_score'] = -(1 + candidate_df['interference_level_sum']) / (1 + max_interference)
            candidate_df['intensity_score'] = candidate_df['intensity_sum'] / max_intensity
            candidate_df['interference_score'] = -(1 + candidate_df['interference_level_sum']) / (1 + max_interference)
            
            # Combined score
            candidate_df['score'] = (
                candidate_df['sensitivity_score'] * self.config.SENSITIVITY_WEIGHT +
                candidate_df['specificity_score'] * self.config.SPECIFICITY_WEIGHT
            )
        else:
            candidate_df['score'] = candidate_df['intensity_sum']
            candidate_df['sensitivity_score'] = candidate_df['intensity_sum']
            candidate_df['specificity_score'] = -candidate_df['interference_level_sum']
            candidate_df['intensity_score'] = candidate_df['intensity_sum']
            candidate_df['interference_score'] = -candidate_df['interference_level_sum']
        
        return candidate_df
    
    def select_best_pairs(self, candidate_df: pd.DataFrame) -> Tuple[pd.Series, pd.DataFrame]:
        """Select best ion pairs"""
        # Deduplication
        candidate_df['MSMS_combined'] = candidate_df.apply(
            lambda row: tuple(sorted([row['MSMS1'], row['MSMS2']])), axis=1
        )
        candidate_df = candidate_df.loc[candidate_df.groupby('MSMS_combined')['score'].idxmax()]
        candidate_df = candidate_df.drop(columns=['MSMS_combined'])
        
        # Get best combination
        max_row = candidate_df.loc[candidate_df["score"].idxmax()]
        
        # Get top 5 best combinations (CE conversion will be done in MRMOptimizer)
        max5_rows = candidate_df.nlargest(5, 'score').copy()
        max5_rows = max5_rows.reset_index(drop=True)
        
        return max_row, max5_rows


class IonPairOptimizerNIST:
    """Ion pair optimizer for NIST method"""
    
    def __init__(self, config, interference_calc):
        self.config = config
        self.interference_calc = interference_calc
    
    def filter_and_rank_ions(self, working_group_inchikey: pd.DataFrame) -> pd.DataFrame:
        """Filter and rank ions for NIST method"""
        # Determine which name column to use
        name_col = 'Name_x' if 'Name_x' in working_group_inchikey.columns else 'Name'
        
        # Split working_group_inchikey into three sub-tables by NCE
        working_group_inchikey_low = working_group_inchikey[working_group_inchikey['NCE'] <= 60.0]
        working_group_inchikey_low = working_group_inchikey_low.sort_values('intensity', ascending=False)
        working_group_inchikey_low = working_group_inchikey_low.drop_duplicates([name_col, 'MSMS'], keep='first')
        working_group_inchikey_low = working_group_inchikey_low.head(10)
        
        working_group_inchikey_medium = working_group_inchikey[
            (working_group_inchikey['NCE'] > 60.0) & (working_group_inchikey['NCE'] <= 120.0)
        ]
        working_group_inchikey_medium = working_group_inchikey_medium.sort_values('intensity', ascending=False)
        working_group_inchikey_medium = working_group_inchikey_medium.drop_duplicates([name_col, 'MSMS'], keep='first')
        working_group_inchikey_medium = working_group_inchikey_medium.head(10)
        
        working_group_inchikey_high = working_group_inchikey[working_group_inchikey['NCE'] > 120.0]
        working_group_inchikey_high = working_group_inchikey_high.sort_values('intensity', ascending=False)
        working_group_inchikey_high = working_group_inchikey_high.drop_duplicates([name_col, 'MSMS'], keep='first')
        working_group_inchikey_high = working_group_inchikey_high.head(10)
        
        working_group = pd.concat([working_group_inchikey_low, working_group_inchikey_medium, working_group_inchikey_high], ignore_index=True)
        
        return working_group
    
    def generate_ion_pairs(self, working_group: pd.DataFrame) -> pd.DataFrame:
        """Generate ion pair combinations for NIST method"""
        if len(working_group) < 1:
            return pd.DataFrame()
        
        # Sort by intensity
        working_group_sorted = working_group.sort_values('intensity', ascending=False)
        
        # Deduplicate MSMS with tolerance 0.001 da (keep the one with highest intensity)
        msms_tolerance = 0.001
        unique_ions = []
        used_msms = []
        
        for index, row in working_group_sorted.iterrows():
            msms = row['MSMS']
            # Check if this MSMS is too close to any already selected MSMS
            is_too_close = False
            for used_msms_val in used_msms:
                if abs(msms - used_msms_val) < msms_tolerance:
                    is_too_close = True
                    break
            
            if not is_too_close:
                unique_ions.append(row.to_dict())
                used_msms.append(msms)
        
        if len(unique_ions) < 2:
            return pd.DataFrame()
        
        # Generate ion pair combinations from unique ions
        unique_ions_df = pd.DataFrame(unique_ions).reset_index(drop=True)
        combinations_list = list(combinations(unique_ions_df.iterrows(), 2))
        
        candidate_columns = ['MSMS1', 'intensity1', 'NCE1', 'CE1', 'MSMS2', 'intensity2', 'NCE2', 'CE2']
        candidate_data = []
        
        for (index1, row1), (index2, row2) in combinations_list:
            if row1['MSMS'] != row2['MSMS'] and abs(row1['MSMS'] - row2['MSMS']) >= 2.0:
                candidate_data.append([
                    row1['MSMS'], row1['intensity'], row1['NCE'], row1['CE'],
                    row2['MSMS'], row2['intensity'], row2['NCE'], row2['CE']
                ])
        
        candidate_df = pd.DataFrame(candidate_data, columns=candidate_columns)
        return candidate_df
    
    def calculate_scores(self, candidate_df: pd.DataFrame, different_inchikey_rows_low, 
                        different_inchikey_rows_medium, different_inchikey_rows_high,
                        coverage_low, coverage_medium, coverage_high, coverage_all) -> pd.DataFrame:
        """Calculate scores for NIST method (ion pair mode)"""
        # Calculate interference for each ion pair
        hit_nums = []
        hit_rates = []
        
        for index, row in candidate_df.iterrows():
            hit_num, hit_rate = self.interference_calc.process_combination(
                index, row, different_inchikey_rows_low, different_inchikey_rows_medium, 
                different_inchikey_rows_high, coverage_low, coverage_medium, coverage_high, coverage_all
            )
            hit_nums.append(hit_num)
            hit_rates.append(hit_rate)
        
        candidate_df['hit_num'] = hit_nums
        candidate_df['hit_rate'] = hit_rates
        
        # Calculate intensity sum (two channels combined)
        candidate_df['intensity_sum'] = candidate_df['intensity1'] + candidate_df['intensity2']
        
        # Calculate Sensitivity Score and Specificity Score
        max_intensity_sum = candidate_df['intensity_sum'].max()
        max_hit_num = candidate_df['hit_num'].max()
        
        # Sensitivity Score = current intensity_sum / maximum intensity_sum among all combinations
        if max_intensity_sum > 0:
            candidate_df['sensitivity_score'] = candidate_df['intensity_sum'] / max_intensity_sum
        else:
            candidate_df['sensitivity_score'] = 0
        
        # Specificity Score = 1 - hit_num / maximum hit_num among all combinations, if max hit_num is 0, result is 1
        if max_hit_num > 0:
            candidate_df['specificity_score'] = 1 - candidate_df['hit_num'] / max_hit_num
        else:
            candidate_df['specificity_score'] = 1
        
        # Score = weighted combination of sensitivity_score and specificity_score
        candidate_df['score'] = (
            candidate_df['sensitivity_score'] * self.config.SENSITIVITY_WEIGHT +
            candidate_df['specificity_score'] * self.config.SPECIFICITY_WEIGHT
        )
        
        return candidate_df
    
    def select_best_pairs(self, candidate_df: pd.DataFrame) -> Tuple[pd.Series, pd.DataFrame]:
        """Select best ion pairs for NIST method"""
        # Deduplication by MSMS pair
        candidate_df['MSMS_combined'] = candidate_df.apply(
            lambda row: tuple(sorted([row['MSMS1'], row['MSMS2']])), axis=1
        )
        candidate_df = candidate_df.drop_duplicates(subset='MSMS_combined')
        candidate_df = candidate_df.drop(columns=['MSMS_combined'])
        
        # Get best combination
        max_row = candidate_df.loc[candidate_df["score"].idxmax()]
        max10_rows = candidate_df.nlargest(10, 'score')
        max10_rows = max10_rows.reset_index(drop=True)
        
        return max_row, max10_rows
