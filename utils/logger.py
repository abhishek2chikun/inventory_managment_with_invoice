import logging
import os
from datetime import datetime
import sys

def setup_logger():
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Create a logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # Create handlers
    console_handler = logging.StreamHandler(sys.stdout)
    file_handler = logging.FileHandler(f'logs/app_{datetime.now().strftime("%Y%m%d")}.log')
    
    # Create formatters and add it to handlers
    log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(log_format)
    file_handler.setFormatter(log_format)
    
    # Add handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger 