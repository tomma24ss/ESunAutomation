import RPi.GPIO as GPIO
import time
from datetime import datetime, timedelta
import csv
from src.Invertor.datahandler import DataHandler
from src.Logger.logger import MyLogger

class SolarAutomation:
    def __init__(self, relay_pin, db_file, csv_file_path, vwspotdata_file_path, AANTAL_DUURSTE_UREN_6_24=13, AANTAL_DUURSTE_UREN_0_6=3, OK_TO_SWITCH=False):
        self.relay_pin = relay_pin
        self.db_file = db_file
        self.csv_file_path = csv_file_path
        self.vwspotdata_file_path = vwspotdata_file_path
        self.OK_TO_SWITCH = OK_TO_SWITCH  # Set to True to start the automation
        self.AANTAL_DUURSTE_UREN_6_24 = AANTAL_DUURSTE_UREN_6_24
        self.AANTAL_DUURSTE_UREN_0_6 = AANTAL_DUURSTE_UREN_0_6
        self.data_handler = DataHandler(vwspotdata_file_path)
        self.logger = MyLogger()

        # Set up GPIO
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.relay_pin, GPIO.OUT)

    def check_conditions(self):
        actief = True
        try:
            # Check condition 1: Grid injection < 1500W for 10+ minutes
            wattages = self.data_handler.read_lastdata_txt()
            last_10_wattages = wattages[:10]  # Get the last 10 rows (representing 10 minutes)

            # Convert the wattage values to floats
            wattage_values = [float(row[1]) for row in last_10_wattages]
            self.logger.debug("Avg W for 10 minutes: " + str(sum(wattage_values) / len(wattage_values)))
            if all(wattage < 1500 for wattage in wattage_values):  # All 10 minutes under 1500
                self.logger.debug("10 minutes under 1000W")
                actief = True
            elif all(wattage > 1500 for wattage in wattage_values):  # All 10 minutes above 1500
                self.logger.debug("10 minutes above 1000W")
                actief = False

            # Check condition 2: Duurste uren
            if(self.is_duurste_uren()):
                actief = True
                self.logger.debug("Zit in duurste uren")
        except Exception as e:
            self.logger.error("An error occurred while checking conditions: " + str(e))
            actief = False

        return actief

    # Replace with your actual logic to check if it's duurste uren
    def is_duurste_uren(self):
        try:
            duurste_uren = self.get_duurste_uren()
            hours_array = [row[1] for row in duurste_uren]
            now = datetime.now().strftime("%H")
            # print(hours_array) #debug
            # print(now)
            return now in hours_array
        except Exception as e:
            self.logger.error("An error occurred while checking duurste uren: " + str(e))
            return False

    def get_duurste_uren(self):
        try:
            alle_uren = []
            with open(self.csv_file_path, newline='') as csvfile:
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
            joined = hours_06_to_24[0:self.AANTAL_DUURSTE_UREN_6_24] + hours_00_to_06[0:self.AANTAL_DUURSTE_UREN_0_6]
            joined.sort(key=lambda x: float(x[2]), reverse=True)
            return joined
        except Exception as e:
            self.logger.error("An error occurred while getting duurste uren: " + str(e))
            return []

    def activate_relay(self):
        try:
            GPIO.output(self.relay_pin, GPIO.HIGH)  # Activate the relay
        except Exception as e:
            self.logger.error("An error occurred while activating relay: " + str(e))

    def deactivate_relay(self):
        try:
            GPIO.output(self.relay_pin, GPIO.LOW)  # Deactivate the relay
        except Exception as e:
            self.logger.error("An error occurred while deactivating relay: " + str(e))

    def run(self):
        try:
            self.logger.debug("Checking conditions at minute: " + str(datetime.now()))
            if self.check_conditions():
                self.logger.debug("Pin {} actief".format(self.relay_pin) + " en OK_TO_SWITCH is " + str(self.OK_TO_SWITCH))
                if self.OK_TO_SWITCH:
                    self.activate_relay()
                    self.logger.debug("pin {} aan".format(self.relay_pin))
            else:
                self.logger.debug("Pin {} actief".format(self.relay_pin) + " en OK_TO_SWITCH is " + str(self.OK_TO_SWITCH))
                if self.OK_TO_SWITCH:
                    self.deactivate_relay()
                    self.logger.debug("pin {} uit".format(self.relay_pin))
        except KeyboardInterrupt:
            pass

    def cleanup(self):
        try:
            GPIO.cleanup()
        except Exception as e:
            self.logger.error("An error occurred while cleaning up GPIO: " + str(e))
