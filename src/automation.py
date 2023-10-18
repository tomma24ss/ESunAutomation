import RPi.GPIO as GPIO
from datetime import datetime, timedelta
import csv,os,time, subprocess
from src.Invertor.datahandler import DataHandler
from src.Logger.logger import MyLogger
from src.Handlers.duurste_uren_handler import DuursteUrenHandler
from src.SolarForecast.solar_forecast import SolarProductionForecast
from src.Weather.gettemp import Temp

class SolarBoilerAutomation:
    def __init__(self, relay_pin_heatpump,relay_pin_boiler, db_file, csv_file_path, vwspotdata_file_path,griddata_file_path, weatherdata_file_path, productionforecastdata_file_path, AANTAL_DUURSTE_UREN_6_24=13, AANTAL_DUURSTE_UREN_0_6=3, OK_TO_SWITCH=False, HEATPUMP_TOGGLE_WATTAGE=300, BOILER_TOGGLE_WATTAGE=1200):
        self.relay_pin_heatpump = relay_pin_heatpump
        self.relay_pin_boiler = relay_pin_boiler
        self.db_file = db_file
        self.csv_file_path = csv_file_path
        self.vwspotdata_file_path = vwspotdata_file_path
        self.griddata_file_path = griddata_file_path
        self.weatherdata_file_path = weatherdata_file_path
        self.productionforecastdata_file_path = productionforecastdata_file_path
        self.OK_TO_SWITCH = OK_TO_SWITCH  # Set to True to start the automation
        self.HEATPUMP_TOGGLE_WATTAGE = HEATPUMP_TOGGLE_WATTAGE
        self.BOILER_TOGGLE_WATTAGE = BOILER_TOGGLE_WATTAGE
        self.AANTAL_DUURSTE_UREN_6_24 = AANTAL_DUURSTE_UREN_6_24
        self.AANTAL_DUURSTE_UREN_0_6 = AANTAL_DUURSTE_UREN_0_6
        latitude = 50.93978
        longitude = 3.7994
        inclination = 25  # In degrees
        azimuth = 0  # In degrees
        capacity = 12  # In kWp

        self.temp_handler = Temp(latitude, longitude)
        self.solar_forecast = SolarProductionForecast(latitude, longitude, inclination, azimuth, capacity, productionforecastdata_file_path)
        self.data_handler = DataHandler(vwspotdata_file_path, weatherdata_file_path)
        self.logger = MyLogger()
        self.duurste_uren_handler = DuursteUrenHandler(csv_file_path, AANTAL_DUURSTE_UREN_6_24, AANTAL_DUURSTE_UREN_0_6, self.logger)

        # Set up GPIO
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.relay_pin_heatpump, GPIO.OUT)
        GPIO.setup(self.relay_pin_boiler, GPIO.OUT)

    def check_conditions_Heatpump(self):
        actief = True   
        try:
            # Check condition 1: Grid injection < 600W for 10+ minutes
            wattages = self.data_handler.read_lastdata_txt()
            last_10_wattages = wattages[:10]  # Get the last 10 rows (representing 10 minutes)
            self.logger.debug("Heatpump - Last 10 minutes: " + str(last_10_wattages))
            # Convert the wattage values to floats
            wattage_values = [float(w) for w in last_10_wattages] if last_10_wattages else []
            self.logger.debug("Heatpump - Avg W for 10 minutes: " + str(sum(wattage_values) / len(wattage_values) ))
            if all(wattage < self.HEATPUMP_TOGGLE_WATTAGE for wattage in wattage_values):
                self.logger.debug(f"Heatpump - 10 minutes under {self.HEATPUMP_TOGGLE_WATTAGE}W")
                actief = True
            elif all(wattage > self.HEATPUMP_TOGGLE_WATTAGE for wattage in wattage_values):
                self.logger.debug(f"Heatpump - 10 minutes above {self.HEATPUMP_TOGGLE_WATTAGE}W")
                actief = False

            # TODO
            # Condition 2: Determine the number of hours to be active based on the day-ahead calculation
            # and solar production forecast
            day_ahead_hours_today = self.duurste_uren_handler.get_alle_uren()  # Replace with the actual method
            


            #solar forecast
            # yesterday = datetime.now() - timedelta(days=1)
            # formatted_date = yesterday.strftime("%Y%m%d")
            # yesterday_filename = f"{formatted_date}.txt"
            # solar_production_forecast = self.solar_forecast.readfile(yesterday_filename)['result']['watts']
            # self.logger.debug(f"Heatpump - production forecast: {solar_production_forecast}")


            #weather
            current_date = datetime.now().strftime("%Y%m%d")
            weather_data = self.temp_handler.readfile(f"{current_date}.txt")
            next_day_temperature, next_day_cloudcover = self.temp_handler.filter_next_day_data(weather_data)
    
            avg_temperature = self.temp_handler.calculate_avg_temperature(next_day_temperature)
            
            
            
            
            self.logger.debug(f"Heatpump - Avg temp today: {round(avg_temperature, 2)}")

            # additional_hours = solar_production_forecast // 5  # Increase hours for every 5kWh of solar production forecast
            # active_hours = day_ahead_hours_today + additional_hours

            # Check if you need to be active based on the calculated hours
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
            X_waarde = self.BOILER_TOGGLE_WATTAGE if GPIO.input(self.relay_pin_boiler) ==  GPIO.HIGH else 0
            # until the production of 1 inverter is higher than 400W for 10 minutes
            grid_data = self.get_last_50_grid_data()  # Replace with the actual method to get inverter production
            consecutive_low_minutes = 0
            consecutive_high_minutes = 0

            lastdata = grid_data[-1]
            grid_in_now = float(lastdata['gridin']) if lastdata['gridin'] != 'N/A' else 0
            grid_out_now = float(lastdata['gridout']) if lastdata['gridout'] != 'N/A' else 0
            self.logger.debug("Boiler - Grid in: " + str(grid_in_now) + " Grid out: " + str(grid_out_now))
            for data in grid_data[-10:]:
                grid_in = float(data['gridin']) if data['gridin'] != 'N/A' else 0
                #grid_out = float(data['gridout']) if data['gridout'] != 'N/A' else 0
                if grid_in < X_waarde:
                    consecutive_low_minutes += 1
                    consecutive_high_minutes = 0
                else:
                    consecutive_low_minutes = 0
                    consecutive_high_minutes += 1
                    #self.logger.debug("Boiler - Consecutive high minutes: " + str(consecutive_high_minutes))
                     

                if consecutive_low_minutes >= 10 or consecutive_high_minutes >= 10:
                    break  # Exit the loop if both conditions are met

            if consecutive_high_minutes >= 10:
                actief = True
                self.logger.debug(f"Boiler - 10 minutes above {self.BOILER_TOGGLE_WATTAGE}W grid in")
            else:
                actief = False
                self.logger.debug(f"Boiler - 10 minutes under {self.BOILER_TOGGLE_WATTAGE}W grid in")
                return actief 


            # Check condition 2: Duurste uren
            if(self.duurste_uren_handler.is_duurste_uren()):
                self.logger.debug("Boiler - Zit in duurste uren")
            elif(self.duurste_uren_handler.best_uur_wachten(2)): #2 uur nodig om boiler op te warmen ? wacht nog een uur want gooedkopere uren
                self.logger.debug("Boiler - Best uur wachten")  
            else:
                actief = False
                self.logger.debug("Boiler - Zit niet in duurste uren") #boiler aan
                self.duurste_uren_handler 


        except Exception as e:
            self.logger.error("Boiler - An error occurred while checking conditions: " + str(e))
            actief = True

        return actief
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
                    grid_value = { 'time':  parts[1], 'gridin': parts[2], 'gridout': parts[3]}
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
    def get_cpu_temperature():
        try:
            output = subprocess.check_output(["vcgencmd", "measure_temp"]).decode("utf-8")
            temperature = float(output.strip().replace("temp=", "").replace("'C\n", ""))
            return temperature
        except subprocess.CalledProcessError as e:
            print("Error:", e)
        return None
    def run(self):  
        try:
            self.logger.debug("Checking conditions at minute: " + str(datetime.now()))
            if self.check_conditions_Heatpump(): #
                self.logger.debug("Heatpump: Pin {} actief (niet draaien)".format(self.relay_pin_heatpump) + " en OK_TO_SWITCH is " + str(self.OK_TO_SWITCH))
                if str(self.OK_TO_SWITCH) == "True":
                    self.activate_relay_heatpump()
                    self.logger.debug("Heatpump: Pin {} aan (niet draaien)".format(self.relay_pin_heatpump)) #heatpump pin aan dus moet niet draaien
            else:
                self.logger.debug("Heatpump: Pin {} niet actief (draaien)".format(self.relay_pin_heatpump) + " en OK_TO_SWITCH is " + str(self.OK_TO_SWITCH))
                if str(self.OK_TO_SWITCH) == "True":
                    self.deactivate_relay_heatpump()
                    self.logger.debug("Heatpump: Pin {} uit (draaien)".format(self.relay_pin_heatpump)) #heatpump pin uit dus moet draaien    

            if self.check_conditions_boiler():
                self.logger.debug("Boiler: Pin {} actief (niet draaien)".format(self.relay_pin_boiler) + " en OK_TO_SWITCH is " + str(self.OK_TO_SWITCH))
                if str(self.OK_TO_SWITCH) == "True":
                    self.activate_relay_boiler()
                    self.logger.debug("Boiler: Pin {} aan (niet  draaien)".format(self.relay_pin_boiler)) #boiler pin aan dus moet niet draaien
            else:
                self.logger.debug("Boiler: Pin {} niet actief (draaien)".format(self.relay_pin_boiler) + " en OK_TO_SWITCH is " + str(self.OK_TO_SWITCH))
                if str(self.OK_TO_SWITCH) == "True":
                    self.deactivate_relay_boiler()
                    self.logger.debug("Boiler: Pin {} uit (draaien)".format(self.relay_pin_boiler))  #boiler pin uit dus moet draaien

        except KeyboardInterrupt:
            pass

    def cleanup(self):
        try:
            GPIO.cleanup()
        except Exception as e:
            self.logger.error("An error occurred while cleaning up GPIO: " + str(e))
