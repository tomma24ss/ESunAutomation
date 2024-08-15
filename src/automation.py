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
    
    import os

    import os

    def check_pin_36_active(self, log_directory, filename="pin_states.txt"):
        file_path = os.path.join(log_directory, filename)
        if not os.path.exists(file_path):
            self.logger.error("Pin 36 - Log file does not exist.")
            return False

        pin_36_active = False
        try:
            with open(file_path, 'r') as file:
                lines = file.readlines()
                if not lines:
                    self.logger.error("Pin 36 - Log file is empty.")
                    return False

                # Iterate through lines in reverse to find the last one with "Pin 36"
                last_line_with_pin36 = None
                for line in reversed(lines):
                    if "Pin 36" in line:
                        last_line_with_pin36 = line.strip()
                        break

                if not last_line_with_pin36:
                    self.logger.error("Pin 36 - No line with 'Pin 36' found in the log.")
                    return False

                self.logger.debug(f"Pin 36 - Processing last line: {last_line_with_pin36}")
                parts = last_line_with_pin36.split(' - ')
                if len(parts) < 2:
                    self.logger.error(f"Pin 36 - Skipping malformed line: {last_line_with_pin36}")
                else:
                    pin_info = parts[1].split(':')
                    if len(pin_info) < 2:
                        self.logger.error(f"Pin 36 - Skipping malformed line: {last_line_with_pin36}")
                    else:
                        state_part = pin_info[1].strip()
                        if state_part == "1":
                            pin_36_active = True

        except FileNotFoundError as file_error:
            self.logger.error(f"Pin 36 - File not found: {str(file_error)}")
            return False
        except Exception as e:
            self.logger.error(f"Pin 36 - An error occurred while checking the file: {str(e)}")
            return False

        return pin_36_active
    
    
    def check_pin_35_active(self, log_directory, filename="pin_states.txt"):
        file_path = os.path.join(log_directory, filename)
        if not os.path.exists(file_path):
            self.logger.error("Pin 35 - Log file does not exist.")
            return False

        pin_35_active = False
        try:
            with open(file_path, 'r') as file:
                lines = file.readlines()
                if not lines:
                    self.logger.error("Pin 35 - Log file is empty.")
                    return False

                # Iterate through lines in reverse to find the last one with "Pin 36"
                last_line_with_pin35 = None
                for line in reversed(lines):
                    if "Pin 35" in line:
                        last_line_with_pin35 = line.strip()
                        break

                if not last_line_with_pin35:
                    self.logger.error("Pin 35 - No line with 'Pin 36' found in the log.")
                    return False

                self.logger.debug(f"Pin 35 - Processing last line: {last_line_with_pin35}")
                parts = last_line_with_pin35.split(' - ')
                if len(parts) < 2:
                    self.logger.error(f"Pin 35 - Skipping malformed line: {last_line_with_pin35}")
                else:
                    pin_info = parts[1].split(':')
                    if len(pin_info) < 2:
                        self.logger.error(f"Pin 35 - Skipping malformed line: {last_line_with_pin35}")
                    else:
                        state_part = pin_info[1].strip()
                        if state_part == "0":
                            pin_35_active = True

        except FileNotFoundError as file_error:
            self.logger.error(f"Pin 35 - File not found: {str(file_error)}")
            return False
        except Exception as e:
            self.logger.error(f"Pin 35 - An error occurred while checking the file: {str(e)}")
            return False

        return pin_35_active

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
            
             # Adjust sunrise and sunset times
            adjusted_sunrise = (datetime.combine(now, sunrise) + timedelta(hours=4)).time()
            adjusted_sunset = (datetime.combine(now, sunset) - timedelta(hours=0)).time()

            # Check if current date is within the specified period (1 June to 30 September)
            if now.month >= 4 and now.month <= 9:
                # Check if current time is between sunset and sunrise
                if now.time() > adjusted_sunset or now.time() < adjusted_sunrise:
                    self.logger.debug("Heatpump - Not running during sundown from 1 April to 30 September")
                    return True
                else:
                    self.logger.debug("Heatpump - Continue during sunrise from 1 April to 30 September")
                
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
            #today = datetime.now(datetime.UTC)
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
            self.logger.debug(f"hour of day now(utc): {datetime.utcnow().hour}")
           
            if((datetime.utcnow().hour) in [int(datablock[1]) for datablock in day_ahead_hours_today]):
                self.logger.debug("Heatpump - Zit in duurste uren")
                actief = True
            else: 
                actief = False
                self.logger.debug("Heatpump - Zit niet in duurste uren")

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

            # Adjust sunrise and sunset times
            adjusted_sunrise = (datetime.combine(now, sunrise) + timedelta(hours=4)).time()
            adjusted_sunset = (datetime.combine(now, sunset) - timedelta(hours=0)).time()

            # Check if current date is within the specified period (1 June to 30 September)
            if now.month >= 4 and now.month <= 9:
                # Check if current time is between sunset and sunrise
                if now.time() > adjusted_sunset or now.time() < adjusted_sunrise:
                    self.logger.debug("Boiler - Not running during sundown from 1 April to 30 September")
                    return True
                else:
                    self.logger.debug("Boiler - Continue during sunrise from 1 April to 30 Septembe")
            
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
                self.logger.debug(f"Boiler  - 10 minutes below {lowfeed}W grid in - continue time checks")
            if consecutive_high_minutes_lowfeed >= 10 and boileraan:
                actief = False
                self.logger.debug(f"Boiler - on, 10 minutes above {lowfeed}W grid in")
                return actief 
            if consecutive_high_minutes_highfeed >= 10 and not boileraan:
                actief = False
                self.logger.debug(f"Boiler - on, 10 minutes above {highfeed}W grid in")
                return actief   

            if(self.duurste_uren_handler.is_duurste_uren()):
                actief = True
                self.logger.debug("Boiler - Zit in duurste uren") 
            
            else:
                actief = False
                self.logger.debug("Boiler - Zit niet in duurste uren")
                self.duurste_uren_handler 

        except Exception as e:
            self.logger.error("Boiler - An error occurred while checking conditions: " + str(e))
            actief = True

        return actief
    
    def check_conditions_vent(self):
        actief = True
        local_hour = datetime.now().hour  # Adjusted for local time
        if 7 <= local_hour < 23:
            self.logger.debug("Vent - on between 07:00 and 23:00")
            return False  # Ensures the vent runs during these hours

        try:
            wattages = self.data_handler.read_lastdata_txt()
            last_10_wattages = wattages[:10]
            self.logger.debug("Vent - Last 10 minutes w: " + str(last_10_wattages))
            wattage_values = [float(w) for w in last_10_wattages] if last_10_wattages else []

            if all(wattage < self.HEATPUMP_TOGGLE_WATTAGE for wattage in wattage_values):
                self.logger.debug(f"Vent - last 10 minutes under {self.HEATPUMP_TOGGLE_WATTAGE}W => continue check")
                actief = True
            elif all(wattage > self.HEATPUMP_TOGGLE_WATTAGE for wattage in wattage_values):
                self.logger.debug(f"Vent- on, last 10 minutes above {self.HEATPUMP_TOGGLE_WATTAGE}W")
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
        actief = False
        file_path = '/home/pi/Automation/ESunAutomation/logs/bat_states.txt'
        log_directory = '/home/pi/Automation/ESunAutomation/logs'
        local_hour = datetime.now().hour  # Adjusted for local time
        
        try:
            with open(file_path, 'r') as file:
                lines = file.readlines()
                if not lines:
                    self.logger.debug("Tesla - Battery log file is empty.")
                    return False

                last_line = lines[-1].strip()
                timestamp_str, value = last_line.split(" - ")
                battery_value = float(value)
                time_last_line = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                
                # Check if battery value is recent
                if (datetime.now() - time_last_line) > timedelta(minutes=20):
                    self.logger.debug(f"Tesla - Battery value {battery_value} is not valid because it is too old.")
                    return False
                else:
                    self.logger.debug(f"Tesla - Battery value {battery_value} has correct time check.")
                
                # Check if battery value is between 80 and 75
                if battery_value > 80 or (self.check_pin_35_active(log_directory) and battery_value > 75):
                        self.logger.debug(f"Tesla - Battery value {battery_value} >90 or btw 90 en 95 => Tesla charging active")
                        return True 
                else:
                    self.logger.debug("Tesla - charging OFF")
                    return actief    
                
        except FileNotFoundError as file_error:
            self.logger.error(f"Bat - File not found: {str(file_error)}")
            return False
        except ValueError as value_error:
            self.logger.error(f"Bat - Value error: {str(value_error)}")
            return False
        except Exception as e:
            self.logger.error(f"Bat - An error occurred while checking battery file: {str(e)}")
            return False
        
        #local_hour = datetime.now().hour  # Adjusted for local time
        #if 0 <= local_hour < 24:
            #self.logger.debug("Bat - Bat always ON until on/off when low charge is solved.")
            #return False  
        #return actief

    def check_conditions_Bat(self):
        actief = True
        log_directory = '/home/pi/Automation/ESunAutomation/logs'
        file_path = '/home/pi/Automation/ESunAutomation/logs/bat_states.txt'
        consumption_file = os.path.join(log_directory, "consumption_today.txt")

        try:
            with open(file_path, 'r') as file:
                lines = file.readlines()
                if not lines:
                    self.logger.debug("Bat - Battery log file is empty.")
                    return False

                last_line = lines[-1].strip()
                timestamp_str, value = last_line.split(" - ")
                battery_value = float(value.split()[0])
                time_last_line = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                
                # Check if battery value is recent
                if (datetime.now() - time_last_line) > timedelta(minutes=20):
                    self.logger.debug(f"Bat - Battery value {battery_value} is not valid because it is too old")
                    return False
                else:
                    self.logger.debug(f"Bat - Battery value {battery_value} has correct time check.")
                    
                    # Check if battery value is below 30 or charging and below 35
                    if battery_value < 30:
                        self.logger.debug(f"Bat - Battery value {battery_value} < 30 => activate charge")
                        return False
                    else:
                        if self.check_pin_36_active(log_directory) and battery_value < 35:
                            self.logger.debug(f"Bat - pin 36 active and below 35 => continue charge")
                            return False   

        except FileNotFoundError as file_error:
            self.logger.error(f"Bat - File not found: {str(file_error)}")
            return False
        except ValueError as value_error:
            self.logger.error(f"Bat - Value error: {str(value_error)}")
            return False
        except Exception as e:
            self.logger.error(f"Bat - An error occurred while checking battery file: {str(e)}")
            return False

        if self.check_pin_36_active(log_directory) and (battery_value > 95):
                self.logger.debug("Bat - battery sufficient loaded btw 90 and 95")
                return True              
        
        else:
            if battery_value > 90:
                self.logger.debug(f"Bat - battery sufficient loaded") 
                return True
        
        try:
            bataan = GPIO.input(self.relay_pin_bat) == GPIO.HIGH
            highfeed = 4000
            lowfeed = 200
            grid_data = self.get_last_50_grid_data()
            consecutive_low_minutes_highfeed = 0
            consecutive_high_minutes_highfeed = 0
            consecutive_low_minutes_lowfeed = 0
            consecutive_high_minutes_lowfeed = 0
            lastdata = grid_data[-1]
            grid_in_now = float(lastdata['gridin']) if lastdata['gridin'] != 'N/A' else 0
            grid_out_now = float(lastdata['gridout']) if lastdata['gridout'] != 'N/A' else 0
            self.logger.debug(f"Bat - Grid in: {grid_in_now} Grid out: {grid_out_now}")

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
                
            # Read the consumption data from the file
            consumption_data = []
            consumption_dict = {}

            with open(consumption_file, 'r') as file:
                for line in file:
                    timestamp_str, consumption_str = line.strip().split(" - ")
                    hour = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S").hour
                    consumption = int(float(consumption_str.split()[0]) * 1000)  # Convert kWh to Wh
                    consumption_data.append((hour, consumption))
                    consumption_dict[timestamp_str] = consumption

            # Log the entire consumption data dictionary in one line
            self.logger.debug(f"Consumption data: {consumption_dict}")
    
            # If consumption data is not available, use default
            if not consumption_data:
                self.logger.debug("Bat - No consumption data found, using default.")
                consumption_data = [
                    (0, 350), (1, 350), (2, 350), (3, 350), (4, 450), (5, 350), (6, 350), 
                    (7, 550), (8, 550), (9, 550), (10, 550), (11, 550), (12, 550), (13, 550), 
                    (14, 550), (15, 550), (16, 550), (17, 550), (18, 1000), (19, 1000), 
                    (20, 1000), (21, 1000), (22, 550), (23, 500), (24, 550)
                ]

            battery_forecast_value = battery_value * 100  # Convert to Wh assuming 100% = 10KWh

            current_hour = datetime.now().hour
            forecast_dict = {}

            for hour in range(current_hour, 24):
                consumption = next((c for h, c in consumption_data if h == hour), 0)
                production = solar_production_forecast.get(f"{today} {hour:02d}:00:00", 0)
                
                # Update battery forecast value with reduced production impact
                battery_forecast_value = battery_forecast_value - (consumption * 1) + (production * 0.7)
                battery_forecast_value = max(0, min(10000, battery_forecast_value))  # Clamp between 0 and 10000Wh
                
                # Add the forecast data to the dictionary
                forecast_time_str = f"{today} {hour:02d}:00:00"
                forecast_dict[forecast_time_str] = battery_forecast_value

            # Log the forecast dictionary
            self.logger.debug(f"Bat - battery charge forecast: {forecast_dict}")

            # Get the list of hours sorted by cost or priority
            day_ahead_hours_today = self.duurste_uren_handler.get_duurste_uren(24)
            self.logger.debug(f"Day ahead hours today (before sorting): {day_ahead_hours_today}")

            # Sort by price to ensure cheaper hours are considered first
            day_ahead_hours_today.sort(key=lambda x: float(x[2]))  # Assuming the price is at index 2
            self.logger.debug(f"Day ahead hours today (sorted by price): {day_ahead_hours_today}")

            # Identify hours where battery falls below the threshold
            hours_below_threshold = {hour: value for hour, value in forecast_dict.items() if value < 3000}
            self.logger.debug(f"Bat - Hours with battery forecast below 3000 Wh: {hours_below_threshold}")

            # Assume a charge per hour value of 1kWh
            charge_per_hour = 1000
            remaining_hours_to_charge = []
            updated_forecast_dict = forecast_dict.copy()

            # Work backwards from the first hour that drops below 3000 Wh
            for hour in sorted(hours_below_threshold.keys()):
                while updated_forecast_dict[hour] < 3000:
                    # Select the cheapest available hour that has not been used yet
                    for cheapest_hour in day_ahead_hours_today:
                        cheapest_hour_int = int(cheapest_hour[1])
                        
                        # Ensure the charging hour is close to and before the hour where the battery falls below 3000 Wh
                        if cheapest_hour_int < int(hour.split(" ")[1].split(":")[0]):
                            # Check if this charging hour meaningfully impacts the critical hour
                            future_hour = f"{today} {cheapest_hour_int:02d}:00:00"
                            if future_hour in updated_forecast_dict and updated_forecast_dict[future_hour] + charge_per_hour >= 3000:
                                if cheapest_hour_int not in remaining_hours_to_charge:
                                    # Simulate charging by adding charge and subtracting consumption
                                    consumption = next((c for h, c in consumption_data if h == cheapest_hour_int), 0)
                                    forecast_update = charge_per_hour - consumption
                                    updated_forecast_dict[hour] += forecast_update
                                    remaining_hours_to_charge.append(cheapest_hour_int)
                                    self.logger.debug(f"Bat - Charging at {cheapest_hour_int}:00 to prevent drop below 3000 Wh")
                                    
                                    # Recalculate the forecast for subsequent hours
                                    for h in range(cheapest_hour_int + 1, 24):
                                        h_str = f"{today} {h:02d}:00:00"
                                        if h_str in updated_forecast_dict:
                                            updated_forecast_dict[h_str] = max(0, min(10000, updated_forecast_dict[h_str] + forecast_update))
                                    break
                    else:
                        break  # No valid hour found; exit loop

            self.logger.debug(f"Bat - Selected charging hours: {remaining_hours_to_charge}")
            self.logger.debug(f"Bat - Updated battery charge forecast after planned charging: {updated_forecast_dict}")

            # Final time check using the updated forecast
            if (datetime.utcnow().hour) in remaining_hours_to_charge:
                self.logger.debug("Bat - Currently within selected charging hours")
                actief = False
            else: 
                actief = True
                self.logger.debug("Bat - Currently not within selected charging hours")

        except FileNotFoundError as file_error:
            self.logger.error(f"Bat - File not found: {str(file_error)}")
            actief = False
        except ValueError as value_error:
            self.logger.error(f"Bat - Value error: {str(value_error)}")
            actief = False
        except Exception as e:
            self.logger.error(f"Bat - An error occurred while checking conditions: {str(e)}")
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
                self.logger.debug(f"Tesla: Pin {self.relay_pin_tesla} active (running)")
                if str(self.OK_TO_SWITCH) == "True":
                    self.activate_relay_tesla()
            else:
                self.logger.debug(f"Tesla: Pin {self.relay_pin_tesla} not active (not running)")
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
