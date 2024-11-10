import os
import pandas as pd
import numpy as np
import holidays
from datetime import datetime

# --- Configuration ---
total_yearly_consumption = 4500  # kWh
current_year = datetime.utcnow().year  # Use UTC

# --- Simulate Base Consumption Data ---
date_range = pd.date_range(start=f'{current_year}-01-01', end=f'{current_year}-12-31 23:00:00', freq='H', tz='UTC')
daily_pattern = np.array([0.5, 0.35, 0.35, 0.35, 0.4, 1.0, 0.7, 1.0, 0.8, 0.7, 0.7, 0.7,
                          0.6, 0.6, 0.7, 0.7, 0.8, 1.6, 1.6, 1.6, 0.8, 0.8, 0.6, 0.6])
base_consumption = np.tile(daily_pattern, len(date_range) // 24 + 1)[:len(date_range)]
monthly_adjustment = np.array([1.1, 1.1, 1.0, 0.9, 0.8, 0.7, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2])
seasonal_adjustment = np.repeat(monthly_adjustment, len(date_range) // 12 + 1)[:len(date_range)]
adjusted_consumption = base_consumption * seasonal_adjustment
normalized_consumption = (adjusted_consumption / adjusted_consumption.sum()) * total_yearly_consumption

consumption_df = pd.DataFrame({
    'date_time': date_range,
    'adjusted_consumption_kwh': normalized_consumption
})

# --- Adjust for Belgian Holidays ---
be_holidays = holidays.BE(years=[current_year])
consumption_df['is_holiday'] = consumption_df['date_time'].dt.date.astype('datetime64[ns]').isin(be_holidays)
holiday_adjustment_factor = 1.1
consumption_df.loc[consumption_df['is_holiday'], 'adjusted_consumption_kwh'] *= holiday_adjustment_factor

# --- Weekend Adjustments ---
consumption_df['is_weekend'] = consumption_df['date_time'].dt.dayofweek >= 5
weekend_adjustment_factor = 1.2
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

