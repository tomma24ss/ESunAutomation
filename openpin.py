

import RPi.GPIO as GPIO
import time
from datetime import datetime, time as dt_time

# Set the GPIO mode to BCM
GPIO.setmode(GPIO.BCM)

# Set the pin number you want to control
pin_number = 17  # Change this to your desired pin number

# Set the pin as an output pin
GPIO.setup(pin_number, GPIO.OUT)

# Define the hours during which you want to activate the pin
start_hour = 8   # Change this to your desired start hour (24-hour format)
end_hour = 9    # Change this to your desired end hour (24-hour format)

# Main loop
try:
    while True:
        current_hour = datetime.now().time()
        
        if start_hour <= current_hour < current_hour:
            # Turn the pin on
            GPIO.output(pin_number, GPIO.HIGH)
            print("Pin is ON")
        else:
            # Turn the pin off
            GPIO.output(pin_number, GPIO.LOW)
            print("Pin is OFF")
        
        # Check every minute
        time.sleep(30)
        
except KeyboardInterrupt:
    pass

# Clean up and reset the GPIO configuration
GPIO.cleanup()