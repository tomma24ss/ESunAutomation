import os
import RPi.GPIO as GPIO
import math
from datetime import datetime, timedelta
import csv
import time
import subprocess
from src.Invertor.datahandler import DataHandler
from src.Logger.logger import MyLogger
from src.Handlers.duurste_uren_handler import DuursteUrenHandler
from src.SolarForecast.sunsetconditions import SunsetConditions
from src.SolarForecast.solar_forecast import SolarProductionForecast
from src.Weather.gettemp import Temp
from astral.sun import sun
from astral import LocationInfo

class SolarBoilerAutomation:
    def __init__(self, relay_pin_heatpump, relay_pin_boiler, relay_pin_vent, relay_pin_bat, relay_pin_tesla, db_file, csv_file_path, vwspotdata_file_path, griddata_file_path, weatherdata_file_path, productionforecastdata_file_path, AANTAL_DUURSTE_UREN_6_24=13, AANTAL_DUURSTE_UREN_0_6=3, OK_TO_SWITCH=False, HEATPUMP_TOGGLE_WATTAGE=300, BOILER_TOGGLE_WATTAGE_HIGHFEED=1500, BOILER_TOGGLE_WATTAGE_LOWFEED=300):
        self.relay_pin_heatpump = relay_pin_heatpump
        self.relay_pin_boiler = relay_pin_boiler
        self.relay_pin_vent = relay_pin_vent
        self.relay_pin_bat = relay_pin_bat
        self.relay_pin_tesla = relay_pin_tesla
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
        self.last_bat_on_time = None  # Track the last time battery was set to on
        latitude = 50.93978
        longitude = 3.7994
        inclination = 25  # In degrees
        azimuth = 0  # In degrees
        capacity = 12  # In kWp
        
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.relay_pin_heatpump, GPIO.OUT)
        GPIO.setup(self.relay_pin_boiler, GPIO.OUT)
        GPIO.setup(self.relay_pin_vent, GPIO.OUT)
        GPIO.setup(self.relay_pin_bat, GPIO.OUT)
        GPIO.setup(self.relay_pin_tesla, GPIO.OUT)

        self.temp_handler = Temp(latitude, longitude, weatherdata_file_path)
        self.solar_forecast = SolarProductionForecast(latitude, longitude, inclination, azimuth, capacity, productionforecastdata_file_path)
        self.data_handler = DataHandler(vwspotdata_file_path)
        self.logger = MyLogger()
        self.duurste_uren_handler = DuursteUrenHandler(csv_file_path, AANTAL_DUURSTE_UREN_6_24, AANTAL_DUURSTE_UREN_0_6, self.logger)
        self.sunsetconditions = SunsetConditions(productionforecastdata_file_path, self.logger)
    
    def log_pin_state(self, pin, state):
        directory = '/home/pi/Automation/ESunAutomation/logs'
        filename = os.path.join(directory, "pin_states.txt")
        now = datetime.now()
        ten_minutes_ago = now - timedelta(minutes=10)
        formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")
        state_desc = "1" if state else "0"
        message = f"{formatted_time} - Pin {pin}: {state_desc}\n"

        new_lines = []
        try:
            with open(filename, 'r') as file:
                for line in file:
                    parts = line.strip().split(" - ")
                    if len(parts) > 1:
                        timestamp_str = parts[0]
                        log_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                        if log_time > ten_minutes_ago:
                            new_lines.append(line)
        except FileNotFoundError:
            self.logger.debug("Log file not found, creating new one.")

        with open(filename, 'w') as file:
            file.writelines(new_lines)
            file.write(message)
        self.logger.debug(f"Pin {pin} state ({state_desc}) logged to file.")
    
    def check_pin_36_active(self, log_directory, filename="pin_states.txt"):
        file_path = os.path.join(log_directory, filename)
        if not os.path.exists(file_path):
            print("Log file does not exist.")
            return False

        pin_36_active = False
        with open(file_path, 'r') as file:
            for line in file:
                print("Processing line:", line.strip())
                if "Pin 36" in line:
                    parts = line.split(' - ')
                    if len(parts) < 2:
                        print("Skipping malformed line:", line.strip())
                        continue
                    state_part = parts[1].strip()
                    if state_part.endswith("1"):
                        pin_36_active = True
                        break
        return pin_36_active

    def check_conditions_Heatpump(self):
        actief = True   
        try:
            # Get current date and time
            now = datetime.now()
            
            # Define location (e.g., 'City, Country')
            city = LocationInfo("Oosterzele", "Belgium")
            
            # Get today's sunrise and sunset times
            s = sun(city.observer, date=now)
            sunrise = s['sunrise'].time()
            sunset = s['sunset'].time()
            
            # Check if current date is within the specified period (1 June to 30 September)
            if now.month >= 6 and now.month <= 9:
                # Check if current time is between sunset and sunrise
                
                if now.time() > sunset or now.time() < sunrise:
                    self.logger.debug(f"Heatpump - Past {sunset}, stop")
                    return True
                else:
                    self.logger.debug(f"Heatpump - Past {sunrise}, continue further heatpump checks")
                
            wattages = self.data_handler.read_lastdata_txt()
            last_10_wattages = wattages[:10]
            self.logger.debug("Heatpump - Last 10 minutes w: " + str(last_10_wattages))
            wattage_values = [float(w) for w in last_10_wattages] if last_10_wattages else []
            if all(wattage < self.HEATPUMP_TOGGLE_WATTAGE for wattage in wattage_values):
                self.logger.debug(f"Heatpump - last 10 minutes under {self.HEATPUMP_TOGGLE_WATTAGE}W => go to next heatpump check")
                actief = True
            elif all(wattage > self.HEATPUMP_TOGGLE_WATTAGE for wattage in wattage_values):
                self.logger.debug(f"Heatpump ON - last 10 minutes above {self.HEATPUMP_TOGGLE_WATTAGE}W")
                actief = False
                return actief
            
            log_directory = '/home/pi/Automation/ESunAutomation/logs'
            
            #if self.check_pin_36_active(log_directory) :
                #actief = False
                #self.logger.debug(f"Heatpump aan - because Bat was aan last 10 min => go to boiler")
                #return actief 
    
            feed = 500
            grid_data = self.get_last_50_grid_data()
            consecutive_low_minutes_feed = 0
            consecutive_high_minutes_feed = 0
            lastdata = grid_data[-1]
            grid_in_now = float(lastdata['gridin']) if lastdata['gridin'] != 'N/A' else 0
            grid_out_now = float(lastdata['gridout']) if lastdata['gridout'] != 'N/A' else 0
            self.logger.debug("Heatpump - Grid in: " + str(grid_in_now) + " Grid out: " + str(grid_out_now))

            for data in grid_data[-10:]:
                grid_in = float(data['gridin']) if data['gridin'] != 'N/A' else 0
                if grid_in <= feed:
                    consecutive_low_minutes_feed += 1
                    consecutive_high_minutes_feed = 0
                else:
                    consecutive_low_minutes_feed = 0
                    consecutive_high_minutes_feed += 1
            self.logger.debug(f"Heatpump - gridin minutes above {feed}w : {consecutive_high_minutes_feed}")
            self.logger.debug(f"Heatpump - gridin minutes below {feed}w : {consecutive_low_minutes_feed}")
            
            if consecutive_low_minutes_feed >= 10 : 
                actief = True
                self.logger.debug(f"Heatpump - 10 minutes below {feed}W grid in => go to time check")
            if consecutive_high_minutes_feed >= 10 :
                actief = False
                self.logger.debug(f"Heatpump aan - 10 minutes above {feed}W grid in => go to boiler")
                return actief 
            
            today = datetime.utcnow()
            yesterday = today - timedelta(days=1)
            formatted_date = yesterday.strftime("%Y%m%d")
            yesterday_filename = f"{formatted_date}.txt"

            solar_production_forecast = self.solar_forecast.readfile(yesterday_filename)
            
            watt_today = 0
            if solar_production_forecast is not None:
                solar_production_forecast = solar_production_forecast['result']['watts']
                self.logger.debug(f"Heatpump - production forecast: {solar_production_forecast}")
            
                today = datetime.now().strftime("%Y-%m-%d")
                for datetime_string, wattage in solar_production_forecast.items():
                    if datetime_string.startswith(today):
                        watt_today += wattage
                        
            else:
                self.logger.debug(f"Heatpump - production forecast: No file found.. continuing without production forecast")
            
            self.logger.debug(f"Heatpump - watt_today: {watt_today}")

            weather_data = self.temp_handler.readfile(yesterday_filename)
            if(weather_data is None): raise Exception('weather data of yesterday not found - exciting Heatpump')
            next_day_temperature, next_day_cloudcover = self.temp_handler.filter_next_day_data(weather_data)
            avg_temperature = self.temp_handler.calculate_avg_temperature(next_day_temperature)
            def calculate_added_hours(avg_temperature, threshold_data):
                for threshold, added_hours in threshold_data:
                    if avg_temperature < threshold:
                        return added_hours
                return None
            data = [
                (0, 2),
                (2, 3),
                (5, 8),
                (7, 10),
                (10, 14),
                (15, 18),
                (25, 12),
                (35, 15),
            ]
            amount_hours_chosen = calculate_added_hours(avg_temperature, data)
                       
            amount_added_hours_forecast = math.floor((watt_today - 9000) / 5000)
            self.logger.debug(f"Heatpump - Watt forecast: {watt_today} so added {amount_added_hours_forecast} hours")

            totalhours = amount_hours_chosen + amount_added_hours_forecast
            self.logger.debug(f"Heatpump - Avg T today(pred): {round(avg_temperature, 2)}° so {amount_hours_chosen} hours")
            day_ahead_hours_today = self.duurste_uren_handler.get_duurste_uren(totalhours) 
            self.logger.debug(f"Heatpump - Total hours + forecast: {totalhours}")
            self.logger.debug(f"Heatpump - day_ahead_hours today (already chosen): {day_ahead_hours_today}")
            self.logger.debug(f"hour of day now(utc) + 2uur correctie: {datetime.utcnow().hour + 2}")
           
            if((datetime.utcnow().hour + 2) in [int(datablock[1]) for datablock in day_ahead_hours_today]):
                self.logger.debug("Heatpump - Zit in duurste uren met 2 uur correctie")
                actief = True
            else: 
                actief = False
                self.logger.debug("Heatpump - Zit niet in duurste uren met 2 uur correctie")

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
           # Get current date and time
            now = datetime.now()
            
            # Define location (e.g., 'City, Country')
            city = LocationInfo("Oosterzele", "Belgium")
            
            # Get today's sunrise and sunset times
            s = sun(city.observer, date=now)
            sunrise = s['sunrise'].time()
            sunset = s['sunset'].time()
            
            # Check if current date is within the specified period (1 June to 30 September)
            if now.month >= 6 and now.month <= 9:
                # Check if current time is between sunset and sunrise
                
                if now.time() > sunset or now.time() < sunrise:
                    self.logger.debug("Boiler - Not running during sundown from 1 June to 30 September")
                    return True
                else:
                    self.logger.debug("Boiler - Continue during sunrise from 1 June to 30 September")
            
            boileraan = GPIO.input(self.relay_pin_boiler) == GPIO.HIGH
            highfeed = self.BOILER_TOGGLE_WATTAGE_HIGHFEED
            lowfeed = self.BOILER_TOGGLE_WATTAGE_LOWFEED
            grid_data = self.get_last_50_grid_data()
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
            self.logger.debug(f"Boiler - gridin minutes above {highfeed}w : {consecutive_high_minutes_highfeed}")
            self.logger.debug(f"Boiler - gridin minutes above {lowfeed}w : {consecutive_high_minutes_lowfeed}")
            self.logger.debug(f"Boiler - gridin minutes below {lowfeed}w : {consecutive_low_minutes_lowfeed}")
            
            if consecutive_low_minutes_lowfeed >= 10 and boileraan:
                actief = True
                self.logger.debug(f"Boiler uit want 10 minutes below {lowfeed}W grid in")
            if consecutive_high_minutes_lowfeed >= 10 and boileraan:
                actief = False
                self.logger.debug(f"Boiler aan en blijft aan want 10 minutes above {lowfeed}W grid in")
                return actief 
            if consecutive_high_minutes_highfeed >= 10 and not boileraan:
                actief = False
                self.logger.debug(f"Boiler aan want 10 minutes above {highfeed}W grid in")
                return actief   

            if(self.duurste_uren_handler.is_duurste_uren()):
                actief = True
                self.logger.debug("Boiler - Zit in duurste uren met 2 uur correctie") 
            
            else:
                actief = False
                self.logger.debug("Boiler - Zit niet in duurste uren met 2 uur correctie")
                self.duurste_uren_handler 

        except Exception as e:
            self.logger.error("Boiler - An error occurred while checking conditions: " + str(e))
            actief = True

        return actief
    
    def check_conditions_vent(self):
        actief = True
        local_hour = datetime.now().hour  # Adjusted for local time
        if 7 <= local_hour < 23:
            self.logger.debug("Vent - ON between 07:00 and 23:00")
            return False  # Ensures the vent runs during these hours

        try:
            wattages = self.data_handler.read_lastdata_txt()
            last_10_wattages = wattages[:10]
            self.logger.debug("Vent - Last 10 minutes w: " + str(last_10_wattages))
            wattage_values = [float(w) for w in last_10_wattages] if last_10_wattages else []

            if all(wattage < self.HEATPUMP_TOGGLE_WATTAGE for wattage in wattage_values):
                self.logger.debug(f"Vent - last 10 minutes under {self.HEATPUMP_TOGGLE_WATTAGE}W => go to next vent check")
                actief = True
            elif all(wattage > self.HEATPUMP_TOGGLE_WATTAGE for wattage in wattage_values):
                self.logger.debug(f"Vent on - last 10 minutes above {self.HEATPUMP_TOGGLE_WATTAGE}W => go to bat ")
                actief = False
                return actief

            feed = 20
            grid_data = self.get_last_50_grid_data()
            consecutive_low_minutes_feed = 0
            consecutive_high_minutes_feed = 0
            lastdata = grid_data[-1]
            grid_in_now = float(lastdata['gridin']) if lastdata['gridin'] != 'N/A' else 0
            grid_out_now = float(lastdata['gridout']) if lastdata['gridout'] != 'N/A' else 0
            self.logger.debug("Vent - Grid in: " + str(grid_in_now) + " Grid out: " + str(grid_out_now))

            for data in grid_data[-10:]:
                grid_in = float(data['gridin']) if data['gridin'] != 'N/A' else 0
                if grid_in <= feed:
                    consecutive_low_minutes_feed += 1
                    consecutive_high_minutes_feed = 0
                else:
                    consecutive_low_minutes_feed = 0
                    consecutive_high_minutes_feed += 1

            self.logger.debug(f"Vent - gridin minutes above {feed}W : {consecutive_high_minutes_feed}")
            self.logger.debug(f"Vent - gridin minutes below {feed}W : {consecutive_low_minutes_feed}")
            
            if consecutive_low_minutes_feed >= 10:
                actief = True
                self.logger.debug(f"Vent - 10 minutes below {feed}W grid in => go to bat")
            if consecutive_high_minutes_feed >= 10:
                actief = False
                self.logger.debug(f"Vent - 10 minutes above {feed}W grid in => go to bat")
                return actief

        except FileNotFoundError as file_error:
            self.logger.error("Vent - File not found: " + str(file_error))
            actief = False
        except ValueError as value_error:
            self.logger.error("Vent - Value error: " + str(value_error))
            actief = False
        except Exception as e:
            self.logger.error("Vent - An error occurred while checking conditions: " + str(e))
            actief = False
        return actief

    def check_conditions_Tesla(self):
        actief = True
        local_hour = datetime.now().hour  # Adjusted for local time
        if 1 <= local_hour < 7:
            self.logger.debug("Tesla - ON between 01:00 and 07:00 laden.")
            return False  # Ensures the tesla plug runs during these hours
        else:
            self.logger.debug("Tesla - OFF between 07:00 and 01:00 d+1.")
        return actief

    def check_conditions_Bat(self):
        actief = True   
        
        local_hour = datetime.now().hour  # Adjusted for local time
        if 0 <= local_hour < 24:
            self.logger.debug("Bat - Bat always ON until problems bat charge state solved.")
            return False  
        return actief
        
        try:
            bataan = GPIO.input(self.relay_pin_bat) == GPIO.HIGH
            highfeed = 2500
            lowfeed = 500
            grid_data = self.get_last_50_grid_data()
            consecutive_low_minutes_highfeed = 0
            consecutive_high_minutes_highfeed = 0
            consecutive_low_minutes_lowfeed = 0
            consecutive_high_minutes_lowfeed = 0
            lastdata = grid_data[-1]
            grid_in_now = float(lastdata['gridin']) if lastdata['gridin'] != 'N/A' else 0
            grid_out_now = float(lastdata['gridout']) if lastdata['gridout'] != 'N/A' else 0
            self.logger.debug("Bat - Grid in: " + str(grid_in_now) + " Grid out: " + str(grid_out_now))

            for data in grid_data[-10:]:
                grid_in = float(data['gridin']) if data['gridin'] != 'N/A' else 0
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
            self.logger.debug(f"Bat - gridin minutes above {highfeed}w : {consecutive_high_minutes_highfeed}")
            self.logger.debug(f"Bat - gridin minutes above {lowfeed}w : {consecutive_high_minutes_lowfeed}")
            self.logger.debug(f"Bat - gridin minutes below {lowfeed}w : {consecutive_low_minutes_lowfeed}")
            
            if consecutive_low_minutes_lowfeed >= 10 and bataan:
                actief = True
                self.logger.debug(f"Bat uit - 10 minutes below {lowfeed}W grid in")
            if consecutive_high_minutes_lowfeed >= 10 and bataan:
                actief = False
                self.logger.debug(f"Bat aan - 10 minutes above {lowfeed}W grid in")
                return actief 
            if consecutive_high_minutes_highfeed >= 10 and not bataan:
                actief = False
                self.logger.debug(f"Bat aan - 10 minutes above {highfeed}W grid in")
                return actief   
            
            today = datetime.utcnow()
            yesterday = today - timedelta(days=1)
            formatted_date = yesterday.strftime("%Y%m%d")
            yesterday_filename = f"{formatted_date}.txt"

            solar_production_forecast = self.solar_forecast.readfile(yesterday_filename)
            
            watt_today = 0
            if solar_production_forecast is not None:
                solar_production_forecast = solar_production_forecast['result']['watts']
                self.logger.debug(f"Bat - production forecast: {solar_production_forecast}")
            
                today = datetime.now().strftime("%Y-%m-%d")
                for datetime_string, wattage in solar_production_forecast.items():
                    if datetime_string.startswith(today):
                        watt_today += wattage
                        
            else:
                self.logger.debug(f"Bat - production forecast: No file found.. continuing without production forecast")
            
            self.logger.debug(f"Bat - watt_today: {watt_today}")           
            
            if (watt_today / 2) > 10000:
                self.logger.debug("Bat - time charging off, enough solar today")
                return True  # Do not charge - enough solar today
            else: 
                self.logger.debug(f"Bat - not enough solar today, can use some charging, continue bat checks")
                
            amount_added_hours_forecast = math.floor((10000 - (watt_today / 5)) / 2000)
                        # 10000 is max. van ofwel de capaciteit van de batterij ofwel het gemiddeld dagelijks verbruik
                        # 2000 laad capaciteit van de batterij
            self.logger.debug(f"Bat - Watt forecast: {watt_today} so added {amount_added_hours_forecast} hours")

            totalhours = (24 - amount_added_hours_forecast)
            day_ahead_hours_today = self.duurste_uren_handler.get_duurste_uren(totalhours) 
            self.logger.debug(f"Bat - Total hours: {totalhours}")
            self.logger.debug(f"Bat - day_ahead_hours today (already chosen): {day_ahead_hours_today}")
            self.logger.debug(f"Bat - hour of day now(utc) + 2uur correctie: {datetime.utcnow().hour + 2}")
        
            if (datetime.utcnow().hour + 2) in [int(datablock[1]) for datablock in day_ahead_hours_today]:
                self.logger.debug("Bat - Zit in duurste uren met 2 uur correctie")
                actief = True
            else: 
                actief = False
                self.logger.debug("Bat - Zit niet in duurste uren met 2 uur correctie")

        except FileNotFoundError as file_error:
            self.logger.error("Bat - File not found: " + str(file_error))
            actief = False
        except ValueError as value_error:
            self.logger.error("Bat - Value error: " + str(value_error))
            actief = False
        except Exception as e:
            self.logger.error("Bat - An error occurred while checking conditions: " + str(e))
            actief = False

        return actief
    
    def get_last_50_grid_data(self):
        try:
            current_date = datetime.utcnow().strftime("%Y%m%d")
            data_file_path = os.path.join(self.griddata_file_path, f'{current_date}.txt')
            with open(data_file_path, 'r') as data_file:
                lines = data_file.readlines()
            grid_data = []
            for line in lines[-50:]:
                parts = line.strip().split()
                if len(parts) >= 4:
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
            GPIO.output(self.relay_pin_heatpump, GPIO.LOW)
        except Exception as e:
            self.logger.error("An error occurred while activating relay_heatpump: " + str(e))

    def deactivate_relay_heatpump(self):
        try:
            GPIO.output(self.relay_pin_heatpump, GPIO.HIGH)
        except Exception as e:
            self.logger.error("An error occurred while deactivating relay_heatpump: " + str(e))
    
    def activate_relay_boiler(self):
        try:
            GPIO.output(self.relay_pin_boiler, GPIO.LOW)
        except Exception as e:
            self.logger.error("An error occurred while activating relay_boiler: " + str(e))
    def deactivate_relay_boiler(self):
        try:
            GPIO.output(self.relay_pin_boiler, GPIO.HIGH)
        except Exception as e:
            self.logger.error("An error occurred while deactivating relay_boiler: " + str(e))
    def activate_relay_vent(self):
        try:
            GPIO.output(self.relay_pin_vent, GPIO.LOW)
        except Exception as e:
            self.logger.error("An error occurred while activating relay_vent: " + str(e))   
    def deactivate_relay_vent(self):
        try:
            GPIO.output(self.relay_pin_vent, GPIO.HIGH)
        except Exception as e:
            self.logger.error("An error occurred while deactivating relay_vent: " + str(e))
    def activate_relay_tesla(self):
        try:
            GPIO.output(self.relay_pin_tesla, GPIO.LOW)
        except Exception as e:
            self.logger.error("An error occurred while activating relay_tesla: " + str(e))   
    
    def deactivate_relay_tesla(self):
        try:
            GPIO.output(self.relay_pin_tesla, GPIO.HIGH)
        except Exception as e:
            self.logger.error("An error occurred while deactivating relay_tesla: " + str(e))
    def activate_relay_bat(self):
        try:
            GPIO.output(self.relay_pin_bat, GPIO.LOW)
        except Exception as e:
            self.logger.error("An error occurred while activating relay_bat: " + str(e))   
    def deactivate_relay_bat(self):
        try:
            GPIO.output(self.relay_pin_bat, GPIO.HIGH)
        except Exception as e:
            self.logger.error("An error occurred while deactivating relay_bat: " + str(e))
    
    def run(self):  
        try:
            self.logger.debug("Checking conditions at minute: " + str(datetime.utcnow()))
            self.logger.debug(f"OK_TO_SWITCH: {str(self.OK_TO_SWITCH)}")

            if self.check_conditions_Heatpump():
                self.logger.debug(f"Heatpump: Pin {self.relay_pin_heatpump} active (not running)")
                if str(self.OK_TO_SWITCH) == "True":
                    self.activate_relay_heatpump()
            else:
                self.logger.debug(f"Heatpump: Pin {self.relay_pin_heatpump} not active (running)")
                if str(self.OK_TO_SWITCH) == "True":
                    self.deactivate_relay_heatpump()

            if self.check_conditions_boiler():
                self.logger.debug(f"Boiler: Pin {self.relay_pin_boiler} active (not running)")
                if str(self.OK_TO_SWITCH) == "True":
                    self.activate_relay_boiler()
            else:
                self.logger.debug(f"Boiler: Pin {self.relay_pin_boiler} not active (running)")
                if str(self.OK_TO_SWITCH) == "True":
                    self.deactivate_relay_boiler()

            if self.check_conditions_vent():
                self.logger.debug(f"Vent: Pin {self.relay_pin_vent} active (not running)")
                if str(self.OK_TO_SWITCH) == "True":
                    self.activate_relay_vent()
            else:
                self.logger.debug(f"Vent: Pin {self.relay_pin_vent} not active (running)")
                if str(self.OK_TO_SWITCH) == "True":
                    self.deactivate_relay_vent()

            if self.check_conditions_Tesla():
                self.logger.debug(f"Tesla: Pin {self.relay_pin_tesla} active (not running)")
                if str(self.OK_TO_SWITCH) == "True":
                    self.activate_relay_tesla()
            else:
                self.logger.debug(f"Tesla: Pin {self.relay_pin_tesla} not active (running)")
                if str(self.OK_TO_SWITCH) == "True":
                    self.deactivate_relay_tesla()
            if self.check_conditions_Bat():
                self.logger.debug(f"Bat: Pin {self.relay_pin_bat} active (not running)")
                if str(self.OK_TO_SWITCH) == "True":
                    self.activate_relay_bat()
            else:
                self.logger.debug(f"Bat: Pin {self.relay_pin_bat} not active (running)")
                if str(self.OK_TO_SWITCH) == "True":
                    self.deactivate_relay_bat()
                
            self.log_pin_state(self.relay_pin_heatpump, GPIO.input(self.relay_pin_heatpump))
            self.log_pin_state(self.relay_pin_boiler, GPIO.input(self.relay_pin_boiler))
            self.log_pin_state(self.relay_pin_vent, GPIO.input(self.relay_pin_vent))
            self.log_pin_state(self.relay_pin_bat, GPIO.input(self.relay_pin_bat))
            self.log_pin_state(self.relay_pin_tesla, GPIO.input(self.relay_pin_tesla))
        
        except KeyboardInterrupt:
            pass
        except Exception as e:
            self.logger.error(f"An error occurred while running the automation: {str(e)}")