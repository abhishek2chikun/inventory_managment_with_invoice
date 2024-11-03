import logging
import os
from datetime import datetime

def setup_logger():
    if not os.path.exists('logs'):
        os.makedirs('logs')
        
    logging.basicConfig(
        filename=f'logs/app_{datetime.now().strftime("%Y%m%d")}.log',
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__) 