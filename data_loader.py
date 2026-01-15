#!/usr/bin/env python
# coding: utf-8

"""
Data loading module for MRM Transition Optimization Tool
"""

import os
import pandas as pd
import numpy as np
from tqdm import tqdm
import gc
import pickle
import hashlib
import logging

logger = logging.getLogger(__name__)


class DataLoader:
    """Data loader with optimized memory usage"""
    
    def __init__(self, config):
        self.config = config
        
    def load_demo_data(self) -> pd.DataFrame:
        """Load demo data"""
        logger.info("Reading demo_data.csv...")
        try:
            df = pd.read_csv(self.config.DEMO_DATA_PATH, low_memory=False, encoding='ISO-8859-1')
            logger.info(f"demo_data.csv contains {len(df)} rows of data")
            return df
        except Exception as e:
            logger.error(f"Failed to read demo_data.csv: {e}")
            raise
    
    def load_large_csv(self, folder_path: str, desc: str) -> pd.DataFrame:
        """Load large files from folder (all CSV files) and merge them"""
        logger.info(f"Reading {desc} from folder: {folder_path}...")
        
        # Check if it's a file or folder
        if os.path.isfile(folder_path):
            # If it's a file, use original method
            chunks = []
            try:
                for chunk in tqdm(
                    pd.read_csv(folder_path, chunksize=self.config.CHUNK_SIZE, encoding='utf-8'), 
                    desc=f"Reading {desc}"
                ):
                    chunks.append(chunk)
                    
                df = pd.concat(chunks, ignore_index=True)
                logger.info(f"{desc} contains {len(df)} rows of data")
                
                del chunks
                gc.collect()
                
                return df
            except Exception as e:
                logger.error(f"Failed to read {desc}: {e}")
                raise
        else:
            # If it's a folder, read all CSV files
            if not os.path.isdir(folder_path):
                raise FileNotFoundError(f"Folder not found: {folder_path}")
            
            # Get all CSV files in the folder
            csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
            csv_files.sort()  # Sort for consistent order
            
            if not csv_files:
                raise ValueError(f"No CSV files found in folder: {folder_path}")
            
            logger.info(f"Found {len(csv_files)} CSV files in {folder_path}")
            
            all_chunks = []
            
            try:
                for csv_file in tqdm(csv_files, desc=f"Reading {desc} files"):
                    file_path = os.path.join(folder_path, csv_file)
                    for chunk in pd.read_csv(file_path, chunksize=self.config.CHUNK_SIZE, encoding='utf-8'):
                        all_chunks.append(chunk)
                        
                df = pd.concat(all_chunks, ignore_index=True)
                logger.info(f"{desc} contains {len(df)} rows of data (from {len(csv_files)} files)")
                
                # Clean up memory
                del all_chunks
                gc.collect()
                
                return df
            except Exception as e:
                logger.error(f"Failed to read {desc} from folder {folder_path}: {e}")
                raise


class LazyFileLoader:
    """Lazy file loader that queries data on-demand without loading everything into memory"""
    
    def __init__(self, config):
        self.config = config
        self.index_cache_dir = '.index_cache'
        os.makedirs(self.index_cache_dir, exist_ok=True)
        self.file_indexes = {}  # Cache file indexes
    
    def _get_index_path(self, source_path: str) -> str:
        """Get index file path"""
        path_hash = hashlib.md5(source_path.encode()).hexdigest()[:16]
        index_name = f"index_{os.path.basename(source_path)}_{path_hash}.pkl"
        return os.path.join(self.index_cache_dir, index_name)
    
    def _build_file_index(self, folder_path: str, desc: str) -> dict:
        """Build index: InChIKey -> list of file_paths"""
        index_path = self._get_index_path(folder_path)
        
        # Check if index exists
        if os.path.exists(index_path):
            logger.info(f"Loading existing index for {desc}...")
            try:
                with open(index_path, 'rb') as f:
                    index = pickle.load(f)
                # Check if index format is correct (should be dict with list values)
                if isinstance(index, dict) and len(index) > 0:
                    sample_key = list(index.keys())[0]
                    # New format: list of file paths (strings)
                    # Old format: list of tuples (file_path, row_offset)
                    if isinstance(index[sample_key], list) and len(index[sample_key]) > 0:
                        if isinstance(index[sample_key][0], str):
                            # New format - OK
                            logger.info(f"Index loaded successfully ({len(index)} unique InChIKeys)")
                            return index
                        else:
                            # Old format - need to rebuild
                            logger.info("Detected old index format, rebuilding with new format...")
                            os.remove(index_path)
                    else:
                        # Invalid format - rebuild
                        logger.info("Invalid index format, rebuilding...")
                        os.remove(index_path)
            except Exception as e:
                logger.warning(f"Error loading index: {e}, rebuilding...")
                if os.path.exists(index_path):
                    os.remove(index_path)
        
        logger.info(f"Building index for {desc} (this may take a while, but only needs to be done once)...")
        index = {}
        
        csv_files = sorted([f for f in os.listdir(folder_path) if f.endswith('.csv')])
        logger.info(f"Indexing {len(csv_files)} files...")
        
        for csv_file in tqdm(csv_files, desc=f"Indexing {desc}"):
            file_path = os.path.join(folder_path, csv_file)
            
            # Read file in chunks and index InChIKeys
            try:
                chunk_count = 0
                for chunk in pd.read_csv(file_path, chunksize=50000, encoding='utf-8', low_memory=False):
                    chunk_count += 1
                    if 'InChIKey' in chunk.columns:
                        # Get unique InChIKeys in this chunk
                        # Convert to string and normalize
                        chunk['InChIKey'] = chunk['InChIKey'].astype(str).str.strip()
                        # Also create cleaned version (without whitespace)
                        chunk['InChIKey_clean'] = chunk['InChIKey'].str.replace(r'\s+', '', regex=True)
                        
                        # Index both original and cleaned versions
                        for inchikey in chunk['InChIKey'].dropna().unique():
                            inchikey = str(inchikey).strip()
                            if inchikey and inchikey != 'nan' and inchikey.lower() != 'none':
                                # Index original format
                                if inchikey not in index:
                                    index[inchikey] = []
                                if file_path not in index[inchikey]:
                                    index[inchikey].append(file_path)
                                
                                # Also index cleaned version (without whitespace)
                                inchikey_clean = inchikey.replace(' ', '').replace('\t', '').replace('\n', '')
                                if inchikey_clean != inchikey and inchikey_clean:
                                    if inchikey_clean not in index:
                                        index[inchikey_clean] = []
                                    if file_path not in index[inchikey_clean]:
                                        index[inchikey_clean].append(file_path)
                        
                        # Also index cleaned versions directly
                        for inchikey_clean in chunk['InChIKey_clean'].dropna().unique():
                            inchikey_clean = str(inchikey_clean).strip()
                            if inchikey_clean and inchikey_clean != 'nan' and inchikey_clean.lower() != 'none':
                                if inchikey_clean not in index:
                                    index[inchikey_clean] = []
                                if file_path not in index[inchikey_clean]:
                                    index[inchikey_clean].append(file_path)
                    # Log progress for large files
                    if chunk_count % 100 == 0:
                        logger.debug(f"  Indexed {chunk_count} chunks from {csv_file}")
            except Exception as e:
                logger.warning(f"Error indexing {csv_file}: {e}")
                continue
        
        # Save index
        with open(index_path, 'wb') as f:
            pickle.dump(index, f)
        logger.info(f"Index saved to {index_path} (contains {len(index)} unique InChIKeys)")
        
        return index
    
    def query_by_inchikey(self, folder_path: str, inchikey: str, desc: str = "") -> pd.DataFrame:
        """Query data by InChIKey - only loads relevant files"""
        # Normalize InChIKey
        inchikey_original = str(inchikey).strip()
        inchikey = inchikey_original
        
        # Build or load index
        if folder_path not in self.file_indexes:
            self.file_indexes[folder_path] = self._build_file_index(folder_path, desc)
        
        index = self.file_indexes[folder_path]
        
        # Try exact match first
        if inchikey not in index:
            # Try case-insensitive search
            inchikey_lower = inchikey.lower()
            found = False
            matching_key = None
            similar_keys = []
            
            for key in index.keys():
                key_str = str(key).strip()
                if key_str.lower() == inchikey_lower:
                    matching_key = key_str
                    found = True
                    break
                # Also collect similar keys for debugging
                if inchikey_lower in key_str.lower() or key_str.lower() in inchikey_lower:
                    similar_keys.append(key_str)
            
            if found:
                inchikey = matching_key
                logger.info(f"Found InChIKey with case-insensitive match: {inchikey}")
            else:
                # Log similar keys for debugging
                if similar_keys:
                    logger.warning(f"InChIKey '{inchikey_original}' not found in index, but found {len(similar_keys)} similar keys (first 5): {similar_keys[:5]}")
                else:
                    logger.warning(f"InChIKey '{inchikey_original}' not found in index (index contains {len(index)} keys)")
                # Don't do full file search to avoid memory issues
                return pd.DataFrame()
        
        # Load only relevant files
        all_data = []
        file_paths = index[inchikey]
        logger.info(f"Found InChIKey '{inchikey}' in {len(file_paths)} file(s)")
        
        for file_path in file_paths:
            try:
                # Read file in chunks and filter
                chunk_count = 0
                for chunk in pd.read_csv(file_path, chunksize=50000, encoding='utf-8', low_memory=False):
                    chunk_count += 1
                    if 'InChIKey' in chunk.columns:
                        # Normalize InChIKey column for comparison
                        chunk['InChIKey'] = chunk['InChIKey'].astype(str).str.strip()
                        # Also create cleaned version for matching
                        chunk['InChIKey_clean'] = chunk['InChIKey'].str.replace(r'\s+', '', regex=True)
                        inchikey_clean = inchikey.replace(' ', '').replace('\t', '').replace('\n', '')
                        
                        # Try multiple matching strategies
                        mask = (
                            (chunk['InChIKey'] == inchikey) |
                            (chunk['InChIKey_clean'] == inchikey_clean) |
                            (chunk['InChIKey'].str.lower() == inchikey.lower())
                        )
                        filtered = chunk[mask]
                        if len(filtered) > 0:
                            all_data.append(filtered)
                            logger.debug(f"Found {len(filtered)} rows in chunk {chunk_count} of {os.path.basename(file_path)}")
            except Exception as e:
                logger.warning(f"Error reading {file_path} for InChIKey {inchikey}: {e}")
                # Fallback: try reading entire file
                try:
                    logger.info(f"Trying to read entire file {os.path.basename(file_path)}...")
                    chunk = pd.read_csv(file_path, encoding='utf-8', low_memory=False)
                    if 'InChIKey' in chunk.columns:
                        chunk['InChIKey'] = chunk['InChIKey'].astype(str).str.strip()
                        filtered = chunk[chunk['InChIKey'] == inchikey]
                        if len(filtered) > 0:
                            all_data.append(filtered)
                            logger.info(f"Found {len(filtered)} rows in {os.path.basename(file_path)}")
                except Exception as e2:
                    logger.warning(f"Fallback read also failed for {file_path}: {e2}")
                    continue
        
        if all_data:
            result = pd.concat(all_data, ignore_index=True)
            logger.info(f"Successfully found {len(result)} total rows for InChIKey {inchikey}")
            return result
        else:
            logger.warning(f"No data found for InChIKey {inchikey} in indexed files")
            return pd.DataFrame()
    
    def query_interference_by_range(self, folder_path: str, precursormz: float, rt: float,
                                   mz_tolerance: float, rt_tolerance: float, 
                                   use_avg_mz: bool = False, desc: str = "") -> pd.DataFrame:
        """Query interference data by m/z and RT range - loads files in chunks"""
        csv_files = sorted([f for f in os.listdir(folder_path) if f.endswith('.csv')])
        all_data = []
        
        # Process files in smaller batches to control memory
        batch_size = 375  # Process files in batches
        for i in range(0, len(csv_files), batch_size):
            batch_files = csv_files[i:i+batch_size]
            batch_data = []
            
            for csv_file in batch_files:
                file_path = os.path.join(folder_path, csv_file)
                try:
                    # Read file in chunks and filter
                    for chunk in pd.read_csv(file_path, chunksize=50000, encoding='utf-8', low_memory=False):
                        if use_avg_mz:
                            if 'Average Mz' in chunk.columns and 'Average Rt(min)' in chunk.columns:
                                mask = (
                                    (abs(chunk['Average Mz'] - precursormz) <= mz_tolerance) &
                                    (abs(chunk['Average Rt(min)'] - rt) <= rt_tolerance)
                                )
                        else:
                            if 'PrecursorMZ' in chunk.columns and 'RT' in chunk.columns:
                                mask = (
                                    (abs(chunk['PrecursorMZ'] - precursormz) <= mz_tolerance) &
                                    (abs(chunk['RT'] - rt) <= rt_tolerance)
                                )
                            else:
                                continue
                        
                        filtered = chunk[mask]
                        if len(filtered) > 0:
                            batch_data.append(filtered)
                except Exception as e:
                    logger.warning(f"Error reading {csv_file}: {e}")
                    continue
            
            if batch_data:
                all_data.append(pd.concat(batch_data, ignore_index=True))
            
            # Clean up after each batch
            del batch_data
            gc.collect()
        
        if all_data:
            result = pd.concat(all_data, ignore_index=True)
            return result
        return pd.DataFrame()
