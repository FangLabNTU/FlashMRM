#!/usr/bin/env python
# coding: utf-8

"""
Validation module for MRM Transition Optimization Tool
Validates user-uploaded interference database format
"""

import os
import pandas as pd
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class InterferenceDBValidator:
    """Validator for interference database format"""
    
    # Required columns for NIST method
    NIST_REQUIRED_COLUMNS = ['InChIKey', 'PrecursorMZ', 'RT', 'MSMS', 'NCE', 'CE', 'Ion_mode', 'Precursor_type']
    
    # Required columns for QE method
    QE_REQUIRED_COLUMNS = ['Alignment ID', 'Average Mz', 'Average Rt(min)', 'CE', 'MS/MS spectrum']
    
    @staticmethod
    def validate_interference_db(db_path: str, method: str = 'nist') -> Tuple[bool, str]:
        """
        Validate interference database format
        
        Args:
            db_path: Path to interference database (file or folder)
            method: Method type ('nist' or 'qe')
        
        Returns:
            (is_valid, error_message)
        """
        if not os.path.exists(db_path):
            return False, f"干扰库路径不存在: {db_path}"
        
        try:
            # Check if it's a file or folder
            if os.path.isfile(db_path):
                # Single file
                if not db_path.endswith('.csv'):
                    return False, f"干扰库文件必须是CSV格式: {db_path}"
                
                # Read first chunk to check columns
                chunk = pd.read_csv(db_path, nrows=100, encoding='utf-8', low_memory=False)
                required_columns = InterferenceDBValidator.NIST_REQUIRED_COLUMNS if method == 'nist' else InterferenceDBValidator.QE_REQUIRED_COLUMNS
                
                missing_columns = [col for col in required_columns if col not in chunk.columns]
                if missing_columns:
                    return False, f"干扰库缺少必需的列: {missing_columns}"
                
                logger.info(f"干扰库文件验证通过: {db_path}")
                return True, "验证通过"
                
            elif os.path.isdir(db_path):
                # Folder with multiple CSV files
                csv_files = [f for f in os.listdir(db_path) if f.endswith('.csv')]
                if not csv_files:
                    return False, f"干扰库文件夹中没有CSV文件: {db_path}"
                
                # Check first file as sample
                sample_file = os.path.join(db_path, csv_files[0])
                chunk = pd.read_csv(sample_file, nrows=100, encoding='utf-8', low_memory=False)
                required_columns = InterferenceDBValidator.NIST_REQUIRED_COLUMNS if method == 'nist' else InterferenceDBValidator.QE_REQUIRED_COLUMNS
                
                missing_columns = [col for col in required_columns if col not in chunk.columns]
                if missing_columns:
                    return False, f"干扰库文件缺少必需的列: {missing_columns} (检查文件: {csv_files[0]})"
                
                logger.info(f"干扰库文件夹验证通过: {db_path} (包含 {len(csv_files)} 个CSV文件)")
                return True, f"验证通过 (包含 {len(csv_files)} 个CSV文件)"
            else:
                return False, f"无效的路径类型: {db_path}"
                
        except Exception as e:
            return False, f"验证干扰库时出错: {str(e)}"
    
    @staticmethod
    def get_db_info(db_path: str) -> dict:
        """
        Get information about the interference database
        
        Args:
            db_path: Path to interference database
        
        Returns:
            Dictionary with database information
        """
        info = {
            'path': db_path,
            'type': 'file' if os.path.isfile(db_path) else 'folder',
            'exists': os.path.exists(db_path),
            'file_count': 0,
            'total_rows': 0
        }
        
        if not info['exists']:
            return info
        
        try:
            if os.path.isfile(db_path):
                info['file_count'] = 1
                # Count rows (approximate)
                chunk_count = 0
                for chunk in pd.read_csv(db_path, chunksize=10000, encoding='utf-8', low_memory=False):
                    chunk_count += len(chunk)
                info['total_rows'] = chunk_count
            else:
                csv_files = [f for f in os.listdir(db_path) if f.endswith('.csv')]
                info['file_count'] = len(csv_files)
                # Count rows from first few files (sample)
                sample_files = csv_files[:5] if len(csv_files) > 5 else csv_files
                for csv_file in sample_files:
                    file_path = os.path.join(db_path, csv_file)
                    for chunk in pd.read_csv(file_path, chunksize=10000, encoding='utf-8', low_memory=False):
                        info['total_rows'] += len(chunk)
        except Exception as e:
            logger.warning(f"获取干扰库信息时出错: {e}")
        
        return info
