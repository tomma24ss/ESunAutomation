

import os
import datetime

class DataHandler:
    def __init__(self, data_folder):
        self.data_folder = os.path.abspath(data_folder)

    def read_date_txt(self, file_path):
        data = []
        try:
            with open(file_path, 'r') as file:
                for line in file:
                    data.append(line.strip().split(','))
        except FileNotFoundError:
            print(f"File not found: {file_path}")
        return data
  

    def read_lastdata_txt(self):
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)

        today_file = os.path.join(self.data_folder, f"{today}.txt")
        if os.path.exists(today_file):
            return self.filter_wattages(self.read_date_txt(today_file))
        # If today's data file is not found, try yesterday's data file
        yesterday_file = os.path.join(self.data_folder, f"{yesterday}.txt")
        if os.path.exists(yesterday_file):
            return self.filter_wattages(self.read_date_txt(yesterday_file))

        raise FileNotFoundError("No data file found for today or yesterday.")
    def filter_wattages(self, data):
        # Assuming the wattages are at positions 25 and 26 in each sub-list
        # You can adjust the positions based on your actual data structure
        filtered_data = []

        for entry in data:
            if len(entry) >= 27:  # Ensure the list is long enough
                wattage_1 = entry[25] # Assuming the wattages are at positions 25 and 26 in each sub-list
                wattage_2 = entry[26] # Assuming the wattages are at positions 25 and 26 in each sub-list
                filtered_data.append([wattage_1, wattage_2])

        return filtered_data
