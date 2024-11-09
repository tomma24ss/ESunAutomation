import requests
import os
import json
from datetime import datetime

class SolarProductionForecast:
    def __init__(self, latitude, longitude, inclination, azimuth, capacity, data_dir = './data'):
        self.latitude = latitude
        self.longitude = longitude
        self.inclination = inclination
        self.azimuth = azimuth
        self.capacity = capacity
        self.data_dir = data_dir

    def get_production_forecast(self):
        # Make an API request to get the production forecast
        url = f"https://api.forecast.solar/estimate/{self.latitude}/{self.longitude}/{self.inclination}/{self.azimuth}/{self.capacity}"
        response = requests.get(url)
        
        if response.status_code == 200:
            return response.json()
        if response.status_code == 429:
            raise Exception(f"API request failed 429 - to many reuests")
        else:
            raise Exception(f"API request failed with status code {response.status_code}")

    def calculate_total_production(self, production_data):
        # Calculate the total production for the day
        total_production = sum(production_data['result']['watt_hours_day'].values())
        return total_production
    def writefile(self, data, filename):

        
        # Ensure the data directory exists
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

        # Create the full path for the data file
        file_path = os.path.join(self.data_dir, filename)

        # Write data to the file
        with open(file_path, 'w') as file:
            json.dump(data, file)

    def readfile(self, filename):
        # Create the full path for the data file
        file_path = os.path.join(self.data_dir, filename)

        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                data = json.load(file)
                return data
        else:
            return None
if __name__ == "__main__":
    # Replace with your latitude, longitude, inclination, azimuth, and capacity
    latitude = 50.939780
    longitude = 3.79940
    inclination = 25  # In degrees
    azimuth = 0  # In degrees
    capacity = 8  # In kWp
    datadir = "/home/pi/Automation/ESunAutomation/src/SolarForecast/data"

    solar_forecast = SolarProductionForecast(latitude, longitude, inclination, azimuth, capacity, datadir)
    production_forecast = solar_forecast.get_production_forecast()

    current_date = datetime.utcnow().strftime("%Y%m%d")
    solar_forecast.writefile(production_forecast, f"{current_date}.txt")

    # Calculate and print the total production for the day
    total_production = solar_forecast.calculate_total_production(production_forecast)
    print(f"{current_date} - Total Solar Production for the Day: {total_production:.2f} Wh")
    
