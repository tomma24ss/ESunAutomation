import RPi.GPIO as GPIO
import math
from datetime import datetime, timedelta
import csv,os,time, subprocess
from src.Invertor.datahandler import DataHandler
from src.Logger.logger import MyLogger
from src.Handlers.duurste_uren_handler import DuursteUrenHandler
from src.SolarForecast.solar_forecast import SolarProductionForecast
from src.Weather.gettemp import Temp

class SolarBoilerAutomation:
    def __init__(self, relay_pin_heatpump,relay_pin_boiler, db_file, csv_file_path, vwspotdata_file_path,griddata_file_path, weatherdata_file_path, productionforecastdata_file_path, AANTAL_DUURSTE_UREN_6_24=13, AANTAL_DUURSTE_UREN_0_6=3, OK_TO_SWITCH=False, HEATPUMP_TOGGLE_WATTAGE=300, BOILER_TOGGLE_WATTAGE_HIGHFEED=1500, BOILER_TOGGLE_WATTAGE_LOWFEED=300):
        self.relay_pin_heatpump = relay_pin_heatpump
        self.relay_pin_boiler = relay_pin_boiler
        self.db_file = db_file
        self.csv_file_path = csv_file_path
        self.vwspotdata_file_path = vwspotdata_file_path
        self.griddata_file_path = griddata_file_path
        self.weatherdata_file_path = weatherdata_file_path
        self.productionforecastdata_file_path = productionforecastdata_file_path
        self.OK_TO_SWITCH = OK_TO_SWITCH  # Set to True to start the automation
        self.HEATPUMP_TOGGLE_WATTAGE = int(HEATPUMP_TOGGLE_WATTAGE)
        self.BOILER_TOGGLE_WATTAGE_HIGHFEED = int(BOILER_TOGGLE_WATTAGE_HIGHFEED)
        self.BOILER_TOGGLE_WATTAGE_LOWFEED = int(BOILER_TOGGLE_WATTAGE_LOWFEED)
        self.AANTAL_DUURSTE_UREN_6_24 = AANTAL_DUURSTE_UREN_6_24
        self.AANTAL_DUURSTE_UREN_0_6 = AANTAL_DUURSTE_UREN_0_6
        latitude = 50.93978
        longitude = 3.7994
        inclination = 25  # In degrees
        azimuth = 0  # In degrees
        capacity = 12  # In kWp
        
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.relay_pin_heatpump, GPIO.OUT)
        GPIO.setup(self.relay_pin_boiler, GPIO.OUT)

        self.temp_handler = Temp(latitude, longitude, weatherdata_file_path)
        self.solar_forecast = SolarProductionForecast(latitude, longitude, inclination, azimuth, capacity, productionforecastdata_file_path)
        self.data_handler = DataHandler(vwspotdata_file_path)
        self.logger = MyLogger()
        self.duurste_uren_handler = DuursteUrenHandler(csv_file_path, AANTAL_DUURSTE_UREN_6_24, AANTAL_DUURSTE_UREN_0_6, self.logger)


    def check_conditions_Heatpump(self):
        actief = True   
        try:
            # Check condition 1: Grid injection < 600W for 10+ minutes
            wattages = self.data_handler.read_lastdata_txt()
            last_10_wattages = wattages[:10]  # Get the last 10 rows (representing 10 minutes)
            self.logger.debug("Heatpump - Last 10 minutes w: " + str(last_10_wattages))
            # Convert the wattage values to floats
            wattage_values = [float(w) for w in last_10_wattages] if last_10_wattages else []
            self.logger.debug("Heatpump - Avg W for 10 minutes: " + str(sum(wattage_values) / len(wattage_values) ))
            if all(wattage < self.HEATPUMP_TOGGLE_WATTAGE for wattage in wattage_values):
                self.logger.debug(f"Heatpump - 10 minutes under {self.HEATPUMP_TOGGLE_WATTAGE}W")
                actief = True
            elif all(wattage > self.HEATPUMP_TOGGLE_WATTAGE for wattage in wattage_values):
                self.logger.debug(f"Heatpump - 10 minutes above {self.HEATPUMP_TOGGLE_WATTAGE}W")
                actief = False
                return actief
    
            #solarforecast
            today = datetime.utcnow()
            yesterday = today - timedelta(days=1)
            formatted_date = yesterday.strftime("%Y%m%d")
            yesterday_filename = f"{formatted_date}.txt"

            solar_production_forecast = self.solar_forecast.readfile(yesterday_filename)
            kwattnow = 0
            if solar_production_forecast is not None:
                solar_production_forecast = solar_production_forecast['result']['watts']
                current_hour = today.strftime('%Y-%m-%d %H:00:00')
                if current_hour in solar_production_forecast:
                    # Get the wattage for the current hour
                    wattage_now = solar_production_forecast[current_hour]
                    print(wattage_now)
                    kwattnow += wattage_now
                
                self.logger.debug(f"Heatpump - production forecast: {solar_production_forecast}")
            else:
                self.logger.debug(f"Heatpump - production forecast: No file found.. continuing without production forecast")

            #weather
            weather_data = self.temp_handler.readfile(yesterday_filename)
            if(weather_data is None): raise Exception('weather data of yesterday not found - exciting Heatpump')
            next_day_temperature, next_day_cloudcover = self.temp_handler.filter_next_day_data(weather_data)
            avg_temperature = self.temp_handler.calculate_avg_temperature(next_day_temperature)
            def calculate_added_hours(avg_temperature, threshold_data):
                for threshold, added_hours in threshold_data:
                    if avg_temperature < threshold:
                        return added_hours
                return None  # Return None if the temperature is higher than all thresholds
            data = [
                (5, 4),
                (10, 8),
                (15, 12),
                (20, 16),
            ]
            amount_hours_chosen = calculate_added_hours(avg_temperature, data)
            amount_added_hours_forecast = math.floor(kwattnow / 5000)
            self.logger.debug(f"Heatpump - KwH forecast: {kwattnow} so {amount_added_hours_forecast} hours")
            totalhours = amount_hours_chosen + amount_added_hours_forecast
            self.logger.debug(f"Heatpump - Avg T today(pred): {round(avg_temperature, 2)}° so {amount_hours_chosen} hours")
            day_ahead_hours_today = self.duurste_uren_handler.get_duurste_uren(totalhours) 
            self.logger.debug(f"Heatpump - Total hours + forecast: {totalhours}")
            self.logger.debug(f"Heatpump - day_ahead_hours today (already chosen): {day_ahead_hours_today}")
            self.logger.debug(f"hour of day now(utc): {datetime.utcnow().hour}")
                    
                    #papa: er is nog een 1h verschil tussen prijzen. Om 21h eemt nog de prijs van 20h, wss door verspringen winteruur
                    
                    #papa: die if statement hieronder werkt niet
           
            if(datetime.utcnow().hour in [int(datablock[1]) for datablock in day_ahead_hours_today]):
                self.logger.debug("Heatpump - Zit in duurste uren van de heatpump")
                actief = True
            else: 
                actief = False
                self.logger.debug("Heatpump - Zit niet in duurste uren van de heatpump")

        except FileNotFoundError as file_error:
            self.logger.error("Heatpump - File not found: " + str(file_error))
            actief = False
        except ValueError as value_error:
            self.logger.error("Heatpump - Value error: " + str(value_error))
            actief = False
        except Exception as e:
            self.logger.error("Heatpump - An error occurred while checking conditions: " + str(e))
            actief = False
        return actief
    
    def check_conditions_boiler(self):
        actief = True
        try:
            boileraan = GPIO.input(self.relay_pin_boiler) ==  GPIO.HIGH
            highfeed = self.BOILER_TOGGLE_WATTAGE_HIGHFEED
            lowfeed = self.BOILER_TOGGLE_WATTAGE_LOWFEED
            # until the production of 1 inverter is higher than 400W for 10 minutes
            grid_data = self.get_last_50_grid_data()  # Replace with the actual method to get inverter production
            consecutive_low_minutes_highfeed = 0
            consecutive_high_minutes_highfeed = 0
            consecutive_low_minutes_lowfeed = 0
            consecutive_high_minutes_lowfeed = 0
            lastdata = grid_data[-1]
            grid_in_now = float(lastdata['gridin']) if lastdata['gridin'] != 'N/A' else 0
            grid_out_now = float(lastdata['gridout']) if lastdata['gridout'] != 'N/A' else 0
            self.logger.debug("Boiler - Grid in: " + str(grid_in_now) + " Grid out: " + str(grid_out_now))
            for data in grid_data[-10:]:
                grid_in = float(data['gridin']) if data['gridin'] != 'N/A' else 0
                #grid_out = float(data['gridout']) if data['gridout'] != 'N/A' else 0
                if grid_in <= highfeed:
                    consecutive_low_minutes_highfeed += 1
                    consecutive_high_minutes_highfeed = 0
                else:
                    consecutive_low_minutes_highfeed = 0
                    consecutive_high_minutes_highfeed += 1
                if grid_in <= lowfeed:
                    consecutive_low_minutes_lowfeed += 1
                    consecutive_high_minutes_lowfeed = 0
                else:
                    consecutive_low_minutes_lowfeed = 0
                    consecutive_high_minutes_lowfeed += 1
                    #self.logger.debug("Boiler - Consecutive high minutes: " + str(consecutive_high_minutes))
                if consecutive_low_minutes_highfeed >= 10 or consecutive_high_minutes_highfeed >= 10:
                    break  # Exit the loop if both conditions are met
            self.logger.debug(f"Boiler - gridin minutes above {highfeed}w : {consecutive_high_minutes_highfeed}")
            self.logger.debug(f"Boiler - gridin minutes above {lowfeed}w : {consecutive_high_minutes_lowfeed}")
            self.logger.debug(f"Boiler - gridin minutes below {lowfeed}w : {consecutive_low_minutes_lowfeed}")
            
            
            if consecutive_low_minutes_lowfeed >= 10 and boileraan: #boiler uit -> kijken naar uren
                actief = True
                self.logger.debug(f"Boiler - 10 minutes below {lowfeed}W grid in")
            if consecutive_high_minutes_lowfeed >= 10 and boileraan:
                actief = False
                self.logger.debug(f"Boiler - 10 minutes above {lowfeed}W grid in") #boiler aan -> niet kijken naar uren
                return actief 
            if consecutive_high_minutes_highfeed >= 10 and not boileraan:
                actief = False
                self.logger.debug(f"Boiler - 10 minutes above {highfeed}W grid in") #boiler aan -> niet kijken naar uren
                return actief   

            # Check condition 2: Duurste uren
            if(self.duurste_uren_handler.is_duurste_uren()):
                actief = True #papa: dit hier bijgezet
                self.logger.debug("Boiler - Zit in duurste uren")
            
            #papa:heb dit in comment gezet voor de éénvoud nu
            #elif(self.duurste_uren_handler.best_uur_wachten(2)): #2 uur nodig om boiler op te warmen ? wacht nog een uur want goedkopere uren
                #actief = True
                #self.logger.debug("Boiler - Best uur wachten")  
            
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
            current_date = datetime.utcnow().strftime("%Y%m%d")
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
            # Set up GPIO
            GPIO.output(self.relay_pin_heatpump, GPIO.LOW)  # Activate the relay
        except Exception as e:
            self.logger.error("An error occurred while activating relay_heatpump: " + str(e))

    def deactivate_relay_heatpump(self):
        try:
            GPIO.output(self.relay_pin_heatpump, GPIO.HIGH)  # Deactivate the relay
        except Exception as e:
            self.logger.error("An error occurred while deactivating relay_heatpump: " + str(e))
    def activate_relay_boiler(self):
        try:
            GPIO.output(self.relay_pin_boiler, GPIO.LOW)  # Activate the relay
        except Exception as e:
            self.logger.error("An error occurred while activating relay_boiler: " + str(e))
    def deactivate_relay_boiler(self):
        try:
            GPIO.output(self.relay_pin_boiler, GPIO.HIGH)  # Deactivate the relay
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
            self.logger.debug("Checking conditions at minute: " + str(datetime.utcnow()))
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
            self.logger.debug("Cleaning up GPIO")
            GPIO.cleanup()
        except Exception as e:
            self.logger.error("An error occurred while cleaning up GPIO: " + str(e))
