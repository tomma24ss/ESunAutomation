import logging
import os
import datetime

class MyLogger:
    def __init__(self, log_directory='/home/pi/Automation/ESunAutomation/logs', log_level=logging.DEBUG):
        self.log_directory = log_directory

        # Create the log directory if it doesn't exist
        if not os.path.exists(self.log_directory):
            os.makedirs(self.log_directory)

        # Create a logger
        self.logger = logging.getLogger('MyLogger')
        self.logger.setLevel(log_level)

        # Create a file handler and set the log level
        log_file = os.path.join(self.log_directory, f"log_{datetime.date.today()}.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)

        # Create a console handler and set the log level
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)

        # Create a formatter and set it for the handlers
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add the handlers to the logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def error(self, message):
        log_message = "\x1b[31mERROR\x1b[0m: " + message  # Red color for errors
        self.logger.error(log_message)

    def warning(self, message):
        log_message = "\x1b[33mWARNING\x1b[0m: " + message  # Yellow color for warnings
        self.logger.warning(log_message)

    def debug(self, message):
        log_message = "\x1b[32mDEBUG\x1b[0m: " + message  # Green color for debug messages
        self.logger.debug(log_message)

    def log(self, level, message):
        # Determine whether to include color codes based on the log destination
        if any(isinstance(handler, logging.StreamHandler) for handler in self.logger.handlers):
            # Log is directed to console (include color codes)
            log_message = message
        else:
            # Log is directed to a file (omit color codes)
            log_message = message.replace('\x1b[31m', '').replace('\x1b[0m', '').replace('\x1b[33m', '').replace('\x1b[32m', '')

        self.logger.log(level, log_message)

# Example usage:
if __name__ == "__main__":
    logger = MyLogger()
    logger.error("This is an error message.")
    logger.warning("This is a warning message.")
    logger.debug("This is a debug message.")
