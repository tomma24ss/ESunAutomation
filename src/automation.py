import RPi.GPIO as GPIO
from datetime import datetime, timedelta
import csv,os,time
from src.Invertor.datahandler import DataHandler
from src.Logger.logger import MyLogger

class SolarBoilerAutomation:
    def __init__(self, relay_pin_heatpump,relay_pin_boiler, db_file, csv_file_path, vwspotdata_file_path,griddata_file_path, AANTAL_DUURSTE_UREN_6_24=13, AANTAL_DUURSTE_UREN_0_6=3, OK_TO_SWITCH=False):
        self.relay_pin_heatpump = relay_pin_heatpump
        self.relay_pin_boiler = relay_pin_boiler
        self.db_file = db_file
        self.csv_file_path = csv_file_path
        self.vwspotdata_file_path = vwspotdata_file_path
        self.griddata_file_path = griddata_file_path
        self.OK_TO_SWITCH = OK_TO_SWITCH  # Set to True to start the automation
        self.AANTAL_DUURSTE_UREN_6_24 = AANTAL_DUURSTE_UREN_6_24
        self.AANTAL_DUURSTE_UREN_0_6 = AANTAL_DUURSTE_UREN_0_6
        self.data_handler = DataHandler(vwspotdata_file_path)
        self.logger = MyLogger()

        # Set up GPIO
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.relay_pin_heatpump, GPIO.OUT)
        GPIO.setup(self.relay_pin_boiler, GPIO.OUT)

    def check_conditions_Heatpump(self):
        actief = True
        try:
            # Check condition 1: Grid injection < 1500W for 10+ minutes
            wattages = self.data_handler.read_lastdata_txt()
            last_10_wattages = wattages[:10]  # Get the last 10 rows (representing 10 minutes)

            # Convert the wattage values to floats
            wattage_values = [float(row[1]) for row in last_10_wattages]
            self.logger.debug("Heatpump - Avg W for 10 minutes: " + str(sum(wattage_values) / len(wattage_values)))
            if all(wattage < 1500 for wattage in wattage_values):  # All 10 minutes under 1500
                self.logger.debug("Heatpump - 10 minutes under 1000W")
                actief = True
            elif all(wattage > 1500 for wattage in wattage_values):  # All 10 minutes above 1500
                self.logger.debug("Heatpump - 10 minutes above 1000W")
                actief = False
            # Condition 2: Determine the number of hours to be active based on the day-ahead calculation
            # and solar production forecast
            # day_ahead_hours = self.calculate_day_ahead_hours()  # Replace with the actual method
            # solar_production_forecast = self.get_solar_production_forecast()  # Replace with the actual method

            # additional_hours = solar_production_forecast // 5  # Increase hours for every 5kWh of solar production forecast
            # active_hours = day_ahead_hours + additional_hours

            # # Check if you need to be active based on the calculated hours
            # current_hour = self.get_current_hour()  # Replace with the actual method to get the current hour
            # if current_hour < active_hours:
            #     actief = True
            # else:
            #     actief = False
        except Exception as e:
            self.logger.error("Heatpump - An error occurred while checking conditions: " + str(e))
            actief = False

        return actief
    
    def check_conditions_boiler(self):
        actief = True
        try:
            # Condition 1: Check if the production of 1 inverter is < 600W for longer than 10 minutes,
            # until the production of 1 inverter is higher than 400W for 10 minutes
            grid_data = self.get_last_50_grid_data()  # Replace with the actual method to get inverter production
            print(grid_data)
            consecutive_low_minutes = 0
            consecutive_high_minutes = 0

            for grid_in in grid_data:
                if grid_in < 600:
                    consecutive_low_minutes += 1
                    consecutive_high_minutes = 0
                else:
                    consecutive_low_minutes = 0
                    consecutive_high_minutes += 1

                if consecutive_low_minutes >= 10 and consecutive_high_minutes >= 10:
                    break  # Exit the loop if both conditions are met

            if consecutive_low_minutes >= 10 and consecutive_high_minutes >= 10:
                actief = True
                self.logger.debug("Boiler - 10 minutes above 600W")
            else:
                actief = False
                self.logger.debug("Boiler - 10 minutes under 600W")

            # Check condition 2: Duurste uren
            if(self.is_duurste_uren()):
                actief = True
                self.logger.debug("Boiler - Zit in duurste uren")

            self.logger.debug("Boiler - Actief for boiler: " + str(actief))

        except Exception as e:
            self.logger.error("Boiler - An error occurred while checking conditions: " + str(e))
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
    def get_last_grid_data(self):
        try:
            # Get the path to the date.txt file for the current day
            current_date = datetime.now().strftime("%Y%m%d")
            data_file_path = os.path.join(self.griddata_file_path, f'{current_date}.txt')

            # Read the contents of the file
            with open(data_file_path, 'r') as data_file:
                lines = data_file.readlines()

            # Extract the last line (last minute) and parse the data
            if lines:
                last_line = lines[-1].strip()
                parts = last_line.split()
                if len(parts) >= 4:  # Ensure there are at least 4 values
                    grid_data = parts[3]
                    return grid_data
                else:
                    self.logger.error("Invalid data format in the last minute of the file.")
            else:
                self.logger.error("No data found in the file for the current day.")

        except Exception as e:
            self.logger.error("An error occurred while getting grid data: " + str(e))

        return "N/A"
    def get_last_50_grid_data(self):
        try:
            # Get the path to the date.txt file for the current day
            current_date = datetime.now().strftime("%Y%m%d")
            data_file_path = os.path.join(self.griddata_file_path, f'{current_date}.txt')

            # Read the contents of the file
            with open(data_file_path, 'r') as data_file:
                lines = data_file.readlines()

            # Extract the last 50 lines (last 50 minutes) and parse the data
            grid_data = []
            for line in lines[-50:]:
                parts = line.strip().split()
                if len(parts) >= 4:  # Ensure there are at least 4 values
                    grid_value = parts[3]
                    grid_data.append(grid_value)
                else:
                    self.logger.error("Invalid data format in a minute of the file.")

            if len(grid_data) < 50:
                self.logger.warning("Less than 50 minutes of data found for the current day.")

            return grid_data

        except Exception as e:
            self.logger.error("An error occurred while getting grid data: " + str(e))

        return ["N/A"] * 50

    def activate_relay_heatpump(self):
        try:
            GPIO.output(self.relay_pin_heatpump, GPIO.HIGH)  # Activate the relay
        except Exception as e:
            self.logger.error("An error occurred while activating relay_heatpump: " + str(e))

    def deactivate_relay_heatpump(self):
        try:
            GPIO.output(self.relay_pin_heatpump, GPIO.LOW)  # Deactivate the relay
        except Exception as e:
            self.logger.error("An error occurred while deactivating relay_heatpump: " + str(e))
    def activate_relay_boiler(self):
        try:
            GPIO.output(self.relay_pin_boiler, GPIO.HIGH)  # Activate the relay
        except Exception as e:
            self.logger.error("An error occurred while activating relay_boiler: " + str(e))
    def deactivate_relay_boiler(self):
        try:
            GPIO.output(self.relay_pin_boiler, GPIO.LOW)  # Deactivate the relay
        except Exception as e:
            self.logger.error("An error occurred while deactivating relay_boiler: " + str(e))
    def run(self):
        try:
            self.logger.debug("Checking conditions at minute: " + str(datetime.now()))
            if self.check_conditions_Heatpump():
                self.logger.debug("Heatpump: Pin {} actief".format(self.relay_pin_heatpump) + " en OK_TO_SWITCH is " + str(self.OK_TO_SWITCH))
                if self.OK_TO_SWITCH:
                    self.activate_relay_heatpump()
                    self.logger.debug("Heatpump: Pin {} aan".format(self.relay_pin_heatpump))
            else:
                self.logger.debug("Heatpump: Pin {} actief".format(self.relay_pin_heatpump) + " en OK_TO_SWITCH is " + str(self.OK_TO_SWITCH))
                if self.OK_TO_SWITCH:
                    self.deactivate_relay_heatpump()
                    self.logger.debug("Heatpump: Pin {} uit".format(self.relay_pin_heatpump))

            if self.check_conditions_boiler():
                self.logger.debug("Boiler: Pin {} actief".format(self.relay_pin_boiler) + " en OK_TO_SWITCH is " + str(self.OK_TO_SWITCH))
                if self.OK_TO_SWITCH:
                    self.activate_relay_boiler()
                    self.logger.debug("Boiler: Pin {} aan".format(self.relay_pin_boiler))
            else:
                self.logger.debug("Boiler: Pin {} actief".format(self.relay_pin_boiler) + " en OK_TO_SWITCH is " + str(self.OK_TO_SWITCH))
                if self.OK_TO_SWITCH:
                    self.deactivate_relay_boiler()
                    self.logger.debug("Boiler: Pin {} uit".format(self.relay_pin_boiler))

        except KeyboardInterrupt:
            pass

    def cleanup(self):
        try:
            GPIO.cleanup()
        except Exception as e:
            self.logger.error("An error occurred while cleaning up GPIO: " + str(e))
