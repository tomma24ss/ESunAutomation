OK_TO_SWITCH =  False # Set to True to start the automation
AANTAL_DUURSTE_UREN_6_24 = 13
AANTAL_DUURSTE_UREN_0_6 = 3
RELAY_PIN_BOILER = 5
CHECK_CONDITIONS_DELAY = 60 # in seconds

# Import libraries
import RPi.GPIO as GPIO
import time
from workflow.invertor import SolarDataHandler
from datetime import datetime, timedelta
import csv

# Set up GPIO
GPIO.setmode(GPIO.BOARD)
GPIO.setup(RELAY_PIN_BOILER, GPIO.OUT)

# Initialize the SolarDataHandler with your database file path
db_file = "../../smadata/SBFspot.db"
csv_file_path = "./Eprices/pricesall.csv"
data_handler = SolarDataHandler(db_file)

# Function to check grid injection and electricity prices conditions
def check_conditions():
    actief = True
    # Check condition 1: Grid injection < 1500W for 10+ minutes
    wattages = data_handler.fetch_pac_data_today() #SolarDataHandler class
    last2_wattage = wattages[0:2] # last 10 minute (2 rows
    print(last2_wattage)
    if(last2_wattage[0][1] < 1500 and last2_wattage[1][1] < 1500): # 10 minuten onder 1500
        print("10 minuten onder W1500. Total W:" + str(last2_wattage[0][1] + last2_wattage[1][1]))
        actief = True
    if(last2_wattage[0][1] > 1500 and last2_wattage[1][1] > 1500): # 10 minuten boven 1500
        print("10 minuten boven W1500. Total W:" + str(last2_wattage[0][1] + last2_wattage[1][1]))
        actief = False

    # Check condition 2: Duurste uren
    if(is_duurste_uren()):
        actief = True
        print("In duurste uren")

    return actief

# Replace with your actual logic to get grid injection data
def get_grid_injection_data():
    data_today = data_handler.fetch_data_today() #SolarDataHandler class
    return data_today

    

# Replace with your actual logic to check if it's duurste uren
def is_duurste_uren():
    duurste_uren = get_duurste_uren()
    hours_array = [row[1] for row in duurste_uren]
    now = datetime.now().strftime("%H")
    print(now)
    print(hours_array)
    print(now in hours_array)
    return now in hours_array

def get_duurste_uren():
    alle_uren = []
    with open(csv_file_path, newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        next(reader, None)  # skip the headers  
        for row in reader:
            alle_uren.append(row)
    start_time = '06'
    end_time = '24'
    end_time_00 = '00'
    hours_06_to_24 = []
    hours_00_to_06 = []
    for row in alle_uren:
        time = row[1].zfill(2)  # Ensure two-digit format with leading zeros
        if start_time <= time <= end_time:
            hours_06_to_24.append(row)
        if end_time_00 <= time < start_time:
            hours_00_to_06.append(row)
    hours_06_to_24.sort(key=lambda x: float(x[2]), reverse=True)
    hours_00_to_06.sort(key=lambda x: float(x[2]), reverse=True)
    joined = hours_06_to_24[0:AANTAL_DUURSTE_UREN_6_24] + hours_00_to_06[0:AANTAL_DUURSTE_UREN_0_6]
    joined.sort(key=lambda x: float(x[2]), reverse=True)
    return joined

# Main loop
try:
        while True:
            if check_conditions():
                if(OK_TO_SWITCH): GPIO.output(RELAY_PIN_BOILER, GPIO.HIGH)  # Activate the relay
                print("pin 5 aan")
            else:
                if(OK_TO_SWITCH): GPIO.output(RELAY_PIN_BOILER, GPIO.LOW)   # Deactivate the relay
                print("pin 5 uit")
            time.sleep(CHECK_CONDITIONS_DELAY)  # Check conditions every minute
except KeyboardInterrupt:
    pass

# Cleanup
data_handler.disconnect()
GPIO.cleanup()