import RPi.GPIO as GPIO
import time
from workflow.invertor import SolarDataHandler
from datetime import datetime, timedelta
import subprocess

# Set up GPIO
GPIO.setmode(GPIO.BOARD)
RELAY_PIN = 5  # Replace with the actual GPIO pin number you want to use
GPIO.setup(RELAY_PIN, GPIO.OUT)

# Initialize the SolarDataHandler with your database file path
db_file = "../smadata/SBFspot.db"  # Adjust the path as needed
data_handler = SolarDataHandler(db_file)

# Function to check grid injection and electricity prices conditions
def check_conditions():
    # Check condition 1: Grid injection < 1500W for 10+ minutes
    # Replace with actual logic to get grid injection data
    grid_injection = get_grid_injection_data()
    if grid_injection < 1500 and is_inactive_for_minutes(grid_injection, 10):
        return True

    # Check condition 2: Duurste uren
    if is_duurste_uren():
        return True

    return False

# Replace with your actual logic to get grid injection data
def get_grid_injection_data():
    # Use the SolarDataHandler class to fetch the data you need
    # Example:
    data_today = data_handler.fetch_data_today()
    return data_today
# Replace with your actual logic to check if a condition is inactive for a specified duration
def is_inactive_for_minutes(data, minutes):
    # Split the data into individual lines
    lines = data.split('\n')
    
    # Initialize variables to keep track of the inactive duration
    inactive_duration = 0
    inactive_threshold = timedelta(minutes=minutes)
    
    # Loop through the data lines in reverse order (from newest to oldest)
    for line in reversed(lines):
        if line:
            # Split the line into fields
            fields = line.split('|')
            
            # Extract the timestamp from the line
            timestamp_str = fields[1]  # Use index 1 for the timestamp
            
            # Convert the timestamp to a datetime object
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            
            # Extract the power output values from the line
            pac1 = float(fields[9])  # Use index 9 for Pac1
            
            # Check if the total power is less than 1500W
            if pac1 < 1500:
                # Increment the inactive duration
                inactive_duration += 5  # Assuming each data point is 5 minutes apart
                
                # Check if the inactive duration has exceeded the threshold
                if inactive_duration >= minutes:
                    return True  # Condition has been inactive for the specified duration
        
            else:
                # Reset the inactive duration if power is above 1500W
                inactive_duration = 0
    
    # If the loop completes without finding the condition, return False
    return False
    

# Replace with your actual logic to check if it's duurste uren
def is_duurste_uren():
    # Use your electricity price script to check if it's duurste uren
    # Example:
    subprocess.call(["./get_electricity_prices.sh"])  # Execute your bash script to get prices
    # Implement logic to check if current time is within duurste uren based on the CSV data
    # Example:
    current_time = time.strftime("%H:%M")
    # Implement your logic to check duurste uren and return True if it matches

# Main loop
try:
    while True:
        if check_conditions():
            GPIO.output(RELAY_PIN, GPIO.HIGH)  # Activate the relay
        else:
            GPIO.output(RELAY_PIN, GPIO.LOW)   # Deactivate the relay
        time.sleep(60)  # Check conditions every minute
except KeyboardInterrupt:
    pass

# Cleanup GPIO
GPIO.cleanup()
