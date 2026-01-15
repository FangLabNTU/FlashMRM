#!/usr/bin/env python
# coding: utf-8

"""
Memory monitoring module for MRM Transition Optimization Tool
"""

import tracemalloc
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class MemoryMonitor:
    """Memory usage monitor"""
    
    def __init__(self):
        self.max_memory_mb = 0
        self.memory_snapshots = []
        tracemalloc.start()
    
    def get_memory_mb(self) -> float:
        """Get current memory usage in MB"""
        current, peak = tracemalloc.get_traced_memory()
        return peak / (1024 * 1024)  # Convert to MB
    
    def snapshot(self, label: str = ""):
        """Take a memory snapshot"""
        current, peak = tracemalloc.get_traced_memory()
        current_mb = current / (1024 * 1024)
        peak_mb = peak / (1024 * 1024)
        
        if peak_mb > self.max_memory_mb:
            self.max_memory_mb = peak_mb
        
        self.memory_snapshots.append({
            'label': label,
            'current_mb': current_mb,
            'peak_mb': peak_mb
        })
        
        return current_mb, peak_mb
    
    def log_snapshot(self, label: str = ""):
        """Take snapshot and log it"""
        current_mb, peak_mb = self.snapshot(label)
        logger.info(f"[内存监控] {label}: 当前={current_mb:.2f} MB, 峰值={peak_mb:.2f} MB")
        return current_mb, peak_mb
    
    def get_summary(self) -> Dict:
        """Get memory usage summary"""
        return {
            'max_memory_mb': self.max_memory_mb,
            'max_memory_gb': self.max_memory_mb / 1024,
            'snapshots': self.memory_snapshots
        }
