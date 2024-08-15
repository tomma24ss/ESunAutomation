import os
import pandas as pd
import numpy as np
import holidays
from datetime import datetime, timedelta
import requests
import matplotlib.pyplot as plt

# --- Configuration ---
API_KEY = '1vtq39nV7ieWFdhS'
LAT = '50.939780'
LON = '3.79940'
URL = f'https://my.meteoblue.com/packages/basic-1h?lat={LAT}&lon={LON}&apikey={API_KEY}&format=json'

total_yearly_consumption = 4500  # kWh
current_year = datetime.utcnow().year  # Use UTC

# --- Function to Fetch Weather Data ---
def get_weather_data():
    try:
        response = requests.get(URL)
        response.raise_for_status()
        data = response.json()

        if 'data_1h' in data:
            weather_data = data['data_1h']
            timestamps = pd.to_datetime(weather_data['time']).tz_localize('UTC')  # Ensure timestamps are in UTC
            weather_df = pd.DataFrame(weather_data)
            weather_df['date_time'] = timestamps
            weather_df['temperature'] = weather_df['temperature']
            weather_df['humidity'] = weather_df['relativehumidity']
            return weather_df[['date_time', 'temperature', 'humidity']]
        else:
            raise KeyError("The 'data_1h' section is missing from the API response.")
    except Exception as e:
        print(f"Error fetching weather data: {e}")
        return None

weather_df = get_weather_data()

if weather_df is None:
    print("Failed to retrieve weather data. Exiting.")
    exit(1)

# --- Simulate Base Consumption Data ---
date_range = pd.date_range(start=f'{current_year}-01-01', end=f'{current_year}-12-31 23:00:00', freq='H', tz='UTC')
daily_pattern = np.array([0.5, 0.3, 0.3, 0.3, 0.4, 0.5, 0.7, 1.0, 0.8, 0.7, 0.7, 0.7,
                          0.6, 0.6, 0.7, 0.7, 0.8, 0.9, 1.0, 0.8, 0.7, 0.6, 0.5, 0.4])
base_consumption = np.tile(daily_pattern, len(date_range) // 24)
monthly_adjustment = np.array([1.1, 1.1, 1.0, 0.9, 0.8, 0.7, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2])
seasonal_adjustment = np.repeat(monthly_adjustment, len(date_range) // 12)
adjusted_consumption = base_consumption * seasonal_adjustment
normalized_consumption = (adjusted_consumption / adjusted_consumption.sum()) * total_yearly_consumption

consumption_df = pd.DataFrame({
    'date_time': date_range,
    'consumption_kwh': normalized_consumption
})

# --- Integrate Weather Data ---
consumption_df = pd.merge(consumption_df, weather_df, on='date_time', how='left')
consumption_df['temperature'].fillna(consumption_df['temperature'].mean(), inplace=True)
consumption_df['humidity'].fillna(consumption_df['humidity'].mean(), inplace=True)
temperature_adjustment = 1 + (20 - consumption_df['temperature']) * 0.01
consumption_df['adjusted_consumption_kwh'] = consumption_df['consumption_kwh'] * temperature_adjustment

# --- Adjust for Belgian Holidays ---
be_holidays = holidays.BE(years=[current_year])
consumption_df['is_holiday'] = consumption_df['date_time'].dt.date.astype('datetime64[ns]').isin(be_holidays)
holiday_adjustment_factor = 1.1
consumption_df.loc[consumption_df['is_holiday'], 'adjusted_consumption_kwh'] *= holiday_adjustment_factor

# --- Weekend Adjustments ---
consumption_df['is_weekend'] = consumption_df['date_time'].dt.dayofweek >= 5
weekend_adjustment_factor = 1.05
consumption_df.loc[consumption_df['is_weekend'], 'adjusted_consumption_kwh'] *= weekend_adjustment_factor

# --- Save Today's Consumption Data to a Text File ---
today = datetime.utcnow().date()  # Use UTC
today_consumption_df = consumption_df[consumption_df['date_time'].dt.date == today]

directory = '/home/pi/Automation/ESunAutomation/logs'
filename = os.path.join(directory, "consumption_today.txt")

# Debugging output
print(f"Saving today's consumption data to {filename}")
print(f"Number of records: {len(today_consumption_df)}")
print(today_consumption_df.head())  # Show the first few records

# Save to file
with open(filename, 'w') as file:
    for index, row in today_consumption_df.iterrows():
        file.write(f"{row['date_time'].strftime('%Y-%m-%d %H:%M:%S')} - {row['adjusted_consumption_kwh']:.2f} kWh\n")

print("Finished saving today's consumption data.")

