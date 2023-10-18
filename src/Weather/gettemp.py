import requests
import os
import json
from datetime import datetime

class Temp:
    def __init__(self, latitude, longitude, data_dir):
        self.latitude = latitude
        self.longitude = longitude
        self.data_dir = data_dir

    def get_weather_data(self):
        # Make an API request to get weather data
        url = f"https://api.open-meteo.com/v1/forecast?latitude={self.latitude}&longitude={self.longitude}&hourly=temperature_2m,cloudcover&forecast_days=2"
        response = requests.get(url)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"TempAPI request failed with status code {response.status_code}")

    def filter_next_day_data(self, weather_data):
        # Extract data for the next day
        hourly_data = weather_data['hourly']
        next_day_temperature = hourly_data['temperature_2m'][24:48]
        next_day_cloudcover = hourly_data['cloudcover'][24:48]

        return next_day_temperature, next_day_cloudcover

    def calculate_avg_temperature(self, temperature_data):
        # Calculate the average temperature
        avg_temperature = sum(temperature_data) / len(temperature_data)
        return avg_temperature
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
    # Replace with your latitude and longitude
    latitude = 50.93978
    longitude = 3.7994
    datadir = "/home/pi/Automation/ESunAutomation/src/Weather/data"

    current_date = datetime.now().strftime("%Y%m%d")
    temp = Temp(latitude, longitude, datadir)
    weather_data = temp.get_weather_data()
    temp.writefile(weather_data, f"{current_date}.txt")
    next_day_temperature, next_day_cloudcover = temp.filter_next_day_data(weather_data)

    # Calculate and print the average temperature for the next day
    avg_temperature = temp.calculate_avg_temperature(next_day_temperature)
    print(f"{current_date} - Average Temperature for the Next Day: {avg_temperature:.2f} °C")

