import requests

class SolarSmartHome:
    def __init__(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude

    def get_weather_data(self):
        # Make an API request to get weather data
        url = f"https://api.open-meteo.com/v1/forecast?latitude={self.latitude}&longitude={self.longitude}&hourly=temperature_2m,cloudcover&forecast_days=2"
        response = requests.get(url)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"API request failed with status code {response.status_code}")

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

if __name__ == "__main__":
    # Replace with your latitude and longitude
    latitude = 50.93978
    longitude = 3.7994

    solar_system = SolarSmartHome(latitude, longitude)
    weather_data = solar_system.get_weather_data()
    next_day_temperature, next_day_cloudcover = solar_system.filter_next_day_data(weather_data)

    # Calculate and print the average temperature for the next day
    avg_temperature = solar_system.calculate_avg_temperature(next_day_temperature)
    print(f"Average Temperature for the Next Day: {avg_temperature:.2f} °C")
