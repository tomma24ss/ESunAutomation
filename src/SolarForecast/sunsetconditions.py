import json
import os
from datetime import datetime, timedelta
import pytz
from pathlib import Path

class SunsetConditions:
    def __init__(self, directory_path, logger):
        self.solar_data = self.read_solar_data(directory_path)
        self.logger = logger

    def read_solar_data(self, directory_path):
        """Read the latest solar data file from a directory."""
        latest_file = self.get_latest_file(directory_path)
        if latest_file:
            with open(latest_file, 'r') as file:
                return json.load(file)
        else:
            return None

    def get_latest_file(self, directory_path):
        """Get the latest file based on the date in the filename."""
        files = [f for f in Path(directory_path).glob('*.txt') if f.is_file()]
        if not files:
            return None
        # Sorting the files based on the date in the filename
        latest_file = max(files, key=lambda x: datetime.strptime(x.stem, '%Y%m%d'))
        return latest_file

    def get_sunrise_sunset(self, date):
        """Get sunrise and sunset times for a given date."""
        if not self.solar_data:
            return None, None
        watts = self.solar_data["result"]["watts"]
        times = [datetime.fromisoformat(time) for time in watts if watts[time] > 0 and time.startswith(date)]
        if times:
            sunrise = min(times)
            sunset = max(times)
            return sunrise, sunset
        return None, None

    def check_conditions_dagnacht(self):
        # Get current date and time
        now = datetime.utcnow().replace(tzinfo=pytz.utc)
        date_str = now.strftime("%Y-%m-%d")

        # Get sunrise and sunset times
        sunrise, sunset = self.get_sunrise_sunset(date_str)

        if sunrise and sunset:
            # Make sunrise and sunset UTC-aware
            adjusted_sunrise = sunrise.replace(tzinfo=pytz.utc) + timedelta(minutes=30)
            adjusted_sunset = sunset.replace(tzinfo=pytz.utc) - timedelta(minutes=30)
            # Check if current time is between adjusted sunrise and sunset
            self.logger.debug(f"Sunrise: {adjusted_sunrise}, Sunset: {adjusted_sunset}, Now: {now}")
            return adjusted_sunrise <= now <= adjusted_sunset

        return False