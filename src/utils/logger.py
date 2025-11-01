#!/usr/bin/env python3
"""
Logging configuration
"""
import logging
import sys
from pathlib import Path


def setup_logger(config: dict) -> logging.Logger:
    """
    Setup logging with file and console handlers
    
    Args:
        config: Logging configuration dict
        
    Returns:
        Configured logger
    """
    # Create logger
    logger = logging.getLogger('jira_scraper')
    logger.setLevel(getattr(logging, config.get('level', 'INFO')))
    
    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler with UTF-8 encoding fix for Windows
    if config.get('console', True):
        # Force UTF-8 encoding for Windows console
        if sys.platform == 'win32':
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler with UTF-8
    if 'file' in config:
        log_file = Path(config['file'])
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger