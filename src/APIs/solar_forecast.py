import requests

class SolarProductionForecast:
    def __init__(self, latitude, longitude, inclination, azimuth, capacity):
        self.latitude = latitude
        self.longitude = longitude
        self.inclination = inclination
        self.azimuth = azimuth
        self.capacity = capacity

    def get_production_forecast(self):
        # Make an API request to get the production forecast
        url = f"https://api.forecast.solar/estimate/{self.latitude}/{self.longitude}/{self.inclination}/{self.azimuth}/{self.capacity}"
        response = requests.get(url)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"API request failed with status code {response.status_code}")

    def calculate_total_production(self, production_data):
        # Calculate the total production for the day
        total_production = sum(production_data['result']['watt_hours_day'].values())
        return total_production

if __name__ == "__main__":
    # Replace with your latitude, longitude, inclination, azimuth, and capacity
    latitude = 50.939780
    longitude = 3.79940
    inclination = 25  # In degrees
    azimuth = 0  # In degrees
    capacity = 12  # In kWp

    solar_forecast = SolarProductionForecast(latitude, longitude, inclination, azimuth, capacity)
    production_forecast = solar_forecast.get_production_forecast()

    # Calculate and print the total production for the day
    total_production = solar_forecast.calculate_total_production(production_forecast)
    print(f"Total Solar Production for the Day: {total_production:.2f} Wh")
    
    # Extract hourly production data from the 'watts' dictionary
    hourly_production = production_forecast['result']['watts']

    # Print hourly production forecast
    print("Hourly Production Forecast:")
    for timestamp, production in hourly_production.items():
        print(f"Timestamp: {timestamp}, Production: {production} W")
