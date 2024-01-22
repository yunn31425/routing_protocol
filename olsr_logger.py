
import logging, os
from datetime import datetime

class OlSRLogger:
    def __init__(self) -> None:  
        log_directory = 'logs'
        os.makedirs(log_directory, exist_ok=True)    
        self.nodeLogger = logging.getLogger("node")
        self.nodeLogger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        log_file_name = './logs/olsr' + datetime.now().strftime('%Y%m%d %H%M%S')+ '.log'
        file_handler = logging.FileHandler(log_file_name, 'a')
        self.nodeLogger.addHandler(file_handler)
        file_handler.setFormatter(formatter)
        
    def debug(self, msg):
        self.nodeLogger.debug(msg)
        
    def info(self, msg):
        self.nodeLogger.info(msg)
        
    def warning(self, msg):
        self.nodeLogger.warning(msg)
        
    def error(self, msg):
        self.nodeLogger.error(msg)
        
    def critical(self, msg):
        self.nodeLogger.critical(msg)
        

if __name__ == '__main__':
    olsr_logger = OlSRLogger()
    olsr_logger.debug('This is a debug message.')
    olsr_logger.info('This is an info message.')
    olsr_logger.warning('This is a warning message.')
    olsr_logger.error('This is an error message.')
    olsr_logger.critical('This is a critical message.')