import re
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime

# Define the log file path
log_file_path = '/home/pi/Automation/ESunAutomation/logs/runlogs/log_2023-11-03.log'

# Regex pattern to find the timestamp and pin status
pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*Pin (\d+).*?(actief|aan)')

# Define a function to parse the log file
def parse_log_file(file_path):
    data = {'timestamp': [], 'pin': [], 'status': []}
    with open(file_path, 'r') as file:
        for line in file:
            match = pattern.search(line)
            if match:
                timestamp = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
                pin = match.group(2)
                status = 1 if 'actief' in match.group(3) else 0  # Assuming 'actief' means active/running
                data['timestamp'].append(timestamp)
                data['pin'].append(pin)
                data['status'].append(status)
    return pd.DataFrame(data)

# Parse the log file
df = parse_log_file(log_file_path)

# Separate the data for each pin
df_heatpump = df[df['pin'] == '31'].copy()
df_boiler = df[df['pin'] == '29'].copy()

# Function to plot the data for a pin
def plot_pin_data(df, pin_number):
    df.set_index('timestamp', inplace=True)
    plt.figure(figsize=(15, 5))
    plt.plot(df.index, df['status'], drawstyle='steps-post')
    plt.xlabel('Time')
    plt.ylabel('Status (Active/Inactive)')
    plt.title(f'Pin {pin_number} Status Over Time')
    plt.yticks([0, 1], ['Inactive', 'Active'])
    plt.grid(True)
    plt.show()

# Plot the data for the heat pump and boiler
plot_pin_data(df_heatpump, '31')
plot_pin_data(df_boiler, '29')
