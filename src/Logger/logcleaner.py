import os
import datetime

# List of directories containing log and txt files
log_directories = [
    '/home/pi/Automation/ESunAutomation/logs/cronlogs', 
    '/home/pi/Automation/ESunAutomation/logs/gridlogs', 
    '/home/pi/Automation/ESunAutomation/logs/invertorlogs', 
    '/home/pi/Automation/ESunAutomation/logs/runlogs', 
    '/home/pi/Automation/ESunAutomation/logs/nextdaypriceslogs', 
    '/home/pi/Automation/ESunAutomation/src/GridPower/griddata',
    '/home/pi/Automation/ESunAutomation/src/Invertor/vwspotdata',
    '/home/pi/Automation/ESunAutomation/src/Eprices',
    '/var/log/sbfspot.3'
]

age_threshold = datetime.timedelta(days=2)  # Set threshold to 14 days as function name suggests

def is_older_than_2_weeks(file_date):
    today = datetime.date.today()
    file_age = today - file_date
    return file_age > age_threshold

def clean_logs(directory):
    for item in os.listdir(directory):
        file_path = os.path.join(directory, item)
        # Check if it's a file and determine type by its pattern
        if os.path.isfile(file_path):
            try:
                if item.startswith("log_") and item.endswith(".log"):
                    file_date_str = item[4:-4]  # 'log_YYYY-MM-DD.log'
                    file_date = datetime.datetime.strptime(file_date_str, '%Y-%m-%d').date()
                elif item.startswith("MyPlant_") and item.endswith(".log"):
                    file_date_str = item[8:-4]  # 'MyPlant_YYYYMMDD.log'
                    file_date = datetime.datetime.strptime(file_date_str, '%Y%m%d').date()
                elif item.endswith(".txt") and len(item) == 14:  # 'YYYY-MM-DD.txt' or 'YYYYMMDD.txt'
                    if '-' in item:
                        file_date_str = item[:-4]  # 'YYYY-MM-DD.txt'
                        file_date = datetime.datetime.strptime(file_date_str, '%Y-%m-%d').date()
                    else:
                        file_date_str = item[:-4]  # 'YYYYMMDD.txt'
                        file_date = datetime.datetime.strptime(file_date_str, '%Y%m%d').date()
                else:
                    continue

                if is_older_than_2_weeks(file_date):
                    print(f"Deleting {file_path}")
                    os.remove(file_path)

            except ValueError:
                print(f"Filename {item} does not match expected date format")

        else:
            print(f"No file found matching expected pattern in {directory}")

for dir_path in log_directories:
    if os.path.exists(dir_path) and os.path.isdir(dir_path):
        clean_logs(dir_path)
    else:
        print(f"Directory {dir_path} does not exist or is not a directory")
