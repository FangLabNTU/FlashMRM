#!/usr/bin/env python
# coding: utf-8

"""
Interference calculation module for MRM Transition Optimization Tool
"""

import pandas as pd
import logging

logger = logging.getLogger(__name__)


class InterferenceCalculatorQE:
    """Interference calculator for QE method"""
    
    def __init__(self, config):
        self.config = config
        self._msms_cache = {}  # Cache for parsed MS/MS spectra
    
    def extract_intensity_from_msms_cached(self, msms_spectrum: str, target_ion: float) -> float:
        """Extract intensity for a specific ion from MS/MS spectrum (with caching)"""
        if pd.isna(msms_spectrum) or msms_spectrum == '':
            return 0.0
        
        # Use cache to avoid repeated parsing
        cache_key = f"{msms_spectrum}_{target_ion}"
        if cache_key in self._msms_cache:
            return self._msms_cache[cache_key]
        
        try:
            peaks = msms_spectrum.split()
            total_intensity = 0.0
            
            for peak in peaks:
                if ':' in peak:
                    parts = peak.split(':', 1)
                    if len(parts) == 2:
                        try:
                            mz = float(parts[0])
                            intensity = float(parts[1])
                            
                            if abs(mz - target_ion) <= self.config.MSMS_TOLERANCE:
                                total_intensity += intensity
                        except (ValueError, IndexError):
                            continue
            
            # Cache result
            self._msms_cache[cache_key] = total_intensity
            return total_intensity
            
        except Exception:
            self._msms_cache[cache_key] = 0.0
            return 0.0


class InterferenceCalculatorNIST:
    """Interference calculator for NIST method"""
    
    def __init__(self, config):
        self.config = config
    
    def process_combination(self, index, row, different_inchikey_rows_low, different_inchikey_rows_medium, 
                           different_inchikey_rows_high, coverage_low, coverage_medium, coverage_high, coverage_all):
        """Interference calculation for NIST method"""
        quan_ion = row['MSMS1']
        quan_ion_intensity = row['intensity1']
        quan_ion_nce = row['NCE1']
        quan_ion_ce = row['CE1']

        qual_ion = row['MSMS2']
        qual_ion_intensity = row['intensity2']
        qual_ion_nce = row['NCE2']
        qual_ion_ce = row['CE2']
        
        # Select coverage based on NCE
        if quan_ion_nce <= 60.0:    
            coverage1 = coverage_low
        elif 60.0 < quan_ion_nce <= 120.0:
            coverage1 = coverage_medium
        elif quan_ion_nce > 120.0:
            coverage1 = coverage_high
        else:
            coverage1 = 0
            
        if qual_ion_nce <= 60.0:    
            coverage2 = coverage_low
        elif 60.0 < qual_ion_nce <= 120.0:
            coverage2 = coverage_medium
        elif qual_ion_nce > 120.0:
            coverage2 = coverage_high
        else:
            coverage2 = 0
        
        coverage = coverage_all

        # Process data for different CE ranges
        result_rows1 = self.process_ce_range(different_inchikey_rows_low, different_inchikey_rows_medium, 
                                           different_inchikey_rows_high, quan_ion, quan_ion_nce)
        result_rows2 = self.process_ce_range(different_inchikey_rows_low, different_inchikey_rows_medium, 
                                           different_inchikey_rows_high, qual_ion, qual_ion_nce)

        common_inchikeys = set(result_rows1["InChIKey"]).union(set(result_rows2["InChIKey"]))
        hit_num = len(common_inchikeys)
        hit_rate = 0
        if coverage != 0:
            hit_rate = len(common_inchikeys)/coverage

        return hit_num, hit_rate
    
    def process_single_ion(self, row, different_inchikey_rows_low, different_inchikey_rows_medium, 
                           different_inchikey_rows_high, coverage_low, coverage_medium, coverage_high, coverage_all):
        """Interference calculation for single ion in NIST method"""
        ion = row['MSMS']
        ion_nce = row['NCE']
        
        # Select coverage based on NCE
        if ion_nce <= 60.0:    
            coverage = coverage_low
        elif 60.0 < ion_nce <= 120.0:
            coverage = coverage_medium
        elif ion_nce > 120.0:
            coverage = coverage_high
        else:
            coverage = 0
        
        # Process data for the CE range
        result_rows = self.process_ce_range(different_inchikey_rows_low, different_inchikey_rows_medium, 
                                           different_inchikey_rows_high, ion, ion_nce)
        
        hit_num = len(result_rows["InChIKey"].unique()) if len(result_rows) > 0 else 0
        hit_rate = 0
        if coverage != 0:
            hit_rate = hit_num / coverage
        
        return hit_num, hit_rate
    
    def process_ce_range(self, different_inchikey_rows_low, different_inchikey_rows_medium, 
                        different_inchikey_rows_high, ion, nce):
        """CE range processing for NIST method"""
        if nce <= 60.0:    
            return different_inchikey_rows_low[abs(ion - different_inchikey_rows_low['MSMS']) <= 1]
        elif 60.0 < nce <= 120.0:
            return different_inchikey_rows_medium[abs(ion - different_inchikey_rows_medium['MSMS']) <= 1]
        elif nce > 120.0:
            return different_inchikey_rows_high[abs(ion - different_inchikey_rows_high['MSMS']) <= 1]
        else:
            return pd.DataFrame()
