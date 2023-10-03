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
db_file = "../../smadata/SBFspot.db"  # Adjust the path as needed
data_handler = SolarDataHandler(db_file)

# Function to check grid injection and electricity prices conditions
def check_conditions():
    # Check condition 1: Grid injection < 1500W for 10+ minutes
    # Replace with actual logic to get grid injection data
    wattages = data_handler.fetch_pac_data_today()
    print(wattages)
    # if grid_injection < 1500 and is_inactive_for_minutes(grid_injection, 10):
    #     return True

    # Check condition 2: Duurste uren
    # if is_duurste_uren():
    #     return True

    return False

# Replace with your actual logic to get grid injection data
def get_grid_injection_data():
    # Use the SolarDataHandler class to fetch the data you need
    # Example:
    data_today = data_handler.fetch_data_today()
    return data_today

    

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
