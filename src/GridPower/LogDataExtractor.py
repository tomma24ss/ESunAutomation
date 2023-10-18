import re
import os
import sys
import glob
from datetime import datetime

sys.path.append('/home/pi/Automation/ESunAutomation/src')
from Logger.logger import MyLogger  # Import the MyLogger class

class LogDataExtractor:
    def __init__(self, log_directory, output_directory, plantname):
        self.log_directory = log_directory
        self.output_directory = output_directory
        self.plantname = plantname
        self.data = None
        self.logger = MyLogger(log_directory='/home/pi/Automation/ESunAutomation/logs/gridlogs')  # Create a logger instance

    def find_latest_log_file(self):
        # Get a list of all log files in the directory
        log_files = glob.glob(os.path.join(self.log_directory, f'{self.plantname}_*.log'))

        if log_files:
            # Sort log files by modification time (newest first)
            log_files.sort(key=os.path.getmtime, reverse=True)
            return log_files[0]  # Return the latest log file
        else:
            return None

    def extract_data(self):
        try:
            # Find the latest log file in the directory
            latest_log_file = self.find_latest_log_file()
            
            if latest_log_file:
                with open(latest_log_file, 'r') as log_file:
                    log_data = log_file.read()
                    #print(log_data)
                pattern = r'\*{20}\n\* ArchiveDayData\(\) \*\n\*{20}([\s\S]*?Inverter Sleep Time\s+:\s+\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})'
                matches = re.findall(pattern, log_data, re.MULTILINE | re.DOTALL)

                lastlog = matches[-1]
                timestamp = self.extract_timestamp(lastlog)
                grid_power_out = self.extract_grid_power_out(lastlog)
                grid_power_in = self.extract_grid_power_in(lastlog)
                #phase_1_pac, uac, iac = self.extract_phase_1_pac_uac_iac(lastlog)

                self.data = [timestamp, grid_power_out, grid_power_in]

            else:
                self.logger.error(f'No log files found in {self.log_directory}')  # Log an error message instead of printing

        except FileNotFoundError:
            self.logger.error(f'Log file not found at {latest_log_file}')  # Log an error message instead of printing
        except Exception as e:
            self.logger.error(f'Error extracting data: {str(e)}')  # Log an error message instead of printing
    
    def extract_timestamp(self, log_data):
        # Find the last "ArchiveDayData()" entry
        pattern = r'Current Inverter Time: (\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})'
        match = re.search(pattern, log_data)
        
        if match:
            current_inverter_time = match.group(1)
            return current_inverter_time
        else:
            self.logger.error(f'No timestamp found in {log_data}')  # Log an error message instead of printing

    def extract_grid_power_out(self, log_data):

        grid_power_out_match = re.search(r'Grid Power Out : (\d+)W', log_data)
        return grid_power_out_match.group(1) if grid_power_out_match else "N/A"

    def extract_grid_power_in(self, log_data):
        grid_power_in_match = re.search(r'Grid Power In  : (\d+)W', log_data)
        return grid_power_in_match.group(1) if grid_power_in_match else "N/A"
  

    def extract_phase_1_pac_uac_iac(self, log_data):
        phase_1_pac_match = re.search(r'Phase 1 Pac : (\d+\.\d+)kW - Uac: (\d+\.\d+)V - Iac: (\d+\.\d+)A', log_data)
        if phase_1_pac_match:
            phase_1_pac = phase_1_pac_match.group(1)
            uac = phase_1_pac_match.group(2)
            iac = phase_1_pac_match.group(3)
            return phase_1_pac, uac, iac
        else:
            return "N/A", "N/A", "N/A"

    def write_data_to_file(self):
        try:
            if not self.data:
                self.logger.warning("No data to write.")  # Log a warning message instead of printing
                return

            # Check if the output directory exists, and create it if not
            if not os.path.exists(self.output_directory):
                os.makedirs(self.output_directory)

            # Get the current date in YYYYMMDD format
            current_date = datetime.now().strftime("%Y%m%d")

            # Define the output file path with the current date
            output_file_path = os.path.join(self.output_directory, f'{current_date}.txt')

            with open(output_file_path, 'a') as output_file:
                # Join the data elements with spaces and write to the file
                output_file.write(' '.join(self.data) + '\n')

            self.logger.debug(f'Data written to {output_file_path}')  # Log an info message instead of printing

        except Exception as e:
            self.logger.error(f'Error writing data: {str(e)}')  # Log an error message instead of printing

# Usage
if __name__ == "__main__":
    log_directory = "/var/log/sbfspot.3"
    output_directory = "/home/pi/Automation/ESunAutomation/src/GridPower/griddata"
    plantname = "Plant"
    extractor = LogDataExtractor(log_directory, output_directory, plantname)
    extractor.extract_data()
    extractor.write_data_to_file()
