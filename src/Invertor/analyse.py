import pandas as pd
import matplotlib.pyplot as plt

# Load the data from the text file into a DataFrame
data = pd.read_csv('data.txt', header=None, names=[
    'Start Time', 'End Time', 'Serial Number', 'Device', 'Serial Number 2', 'Col1', 'Col2', 'Voltage1', 'Voltage2',
    'Voltage3', 'Voltage4', 'Col6', 'Col7', 'Col8', 'Col9', 'Col10', 'Col11', 'Col12', 'Col13', 'Col14', 'Col15',
    'Col16', 'Col17', 'Col18', 'Col19', 'Col20', 'Status', 'Col22', 'Col23'
], parse_dates=['Start Time', 'End Time'])

# Extract the date portion from the 'Start Time' column
data['Date'] = data['Start Time'].dt.date

# Filter the data for a specific date (e.g., 2023-10-05)
selected_date = '2023-10-05'
filtered_data = data[data['Date'] == selected_date]

# Create a plot of the incoming voltages
plt.figure(figsize=(12, 6))
plt.plot(filtered_data['Start Time'], filtered_data['Voltage1'], label='Voltage 1')
plt.plot(filtered_data['Start Time'], filtered_data['Voltage2'], label='Voltage 2')
plt.plot(filtered_data['Start Time'], filtered_data['Voltage3'], label='Voltage 3')
plt.plot(filtered_data['Start Time'], filtered_data['Voltage4'], label='Voltage 4')

plt.title(f'Incoming Voltages on {selected_date}')
plt.xlabel('Time')
plt.ylabel('Voltage')
plt.legend()
plt.grid()

# Show the plot
plt.tight_layout()
plt.show()



