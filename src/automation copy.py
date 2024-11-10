import os
import RPi.GPIO as GPIO
import math
from datetime import datetime, timedelta
import pytz
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
    def __init__(self, relay_pin_heatpump, relay_pin_boiler, relay_pin_vent, relay_pin_bat, relay_pin_tesla, relay_pin_lbs, db_file, csv_file_path, vwspotdata_file_path, griddata_file_path, weatherdata_file_path, productionforecastdata_file_path, AANTAL_DUURSTE_UREN_6_24=13, AANTAL_DUURSTE_UREN_0_6=3, OK_TO_SWITCH=False, HEATPUMP_TOGGLE_WATTAGE=300, BOILER_TOGGLE_WATTAGE_HIGHFEED=1500, BOILER_TOGGLE_WATTAGE_LOWFEED=300):
        self.relay_pin_heatpump = relay_pin_heatpump
        self.relay_pin_boiler = relay_pin_boiler
        self.relay_pin_vent = relay_pin_vent
        self.relay_pin_bat = relay_pin_bat
        self.relay_pin_tesla = relay_pin_tesla
        self.relay_pin_lbs = relay_pin_lbs
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
        self.locked_charging_hour = None
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
        GPIO.setup(self.relay_pin_lbs, GPIO.OUT)

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

    from datetime import datetime, timedelta
    import pytz  # Use pytz for timezone handling
    from astral import LocationInfo
    from astral.sun import sun

    def check_conditions_Heatpump(self):
        actief = True

        try:
            # Get the current local time using pytz for timezone handling
            local_tz = pytz.timezone("Europe/Brussels")  # Use your specific local timezone
            now = datetime.now(local_tz)

            # Define location (e.g., 'City, Country')
            city = LocationInfo("Oosterzele", "Belgium")

            # Get today's sunrise and sunset times in local time
            s = sun(city.observer, date=now)
            sunrise = s['sunrise'].time()
            sunset = s['sunset'].time()

            # Adjust sunrise and sunset times
            adjusted_sunrise = (datetime.combine(now, sunrise) + timedelta(hours=1)).time()
            adjusted_sunset = (datetime.combine(now, sunset) - timedelta(hours=0)).time()

            # Check if current date is within the specified period (1 April to 30 September)
            if now.month >= 4 and now.month <= 8:
                # Check if current time is between sunset and sunrise
                if now.time() > adjusted_sunset or now.time() < adjusted_sunrise:
                    self.logger.debug("Heatpump - Not running during sundown from 1 April to 30 August")
                    return True
                else:
                    self.logger.debug("Heatpump - Continue during sunrise from 1 April to 30 August")

            # Fetch the last 10 minutes of wattage data
            wattages = self.data_handler.read_lastdata_txt()
            last_10_wattages = wattages[:10]
            self.logger.debug("Heatpump - Last 10 minutes w: " + str(last_10_wattages))

            # Process wattage data
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

            if consecutive_low_minutes_feed >= 10:
                actief = True
                self.logger.debug(f"Heatpump - 10 minutes below {feed}W grid in => go to time check")
            if consecutive_high_minutes_feed >= 10:
                actief = False
                self.logger.debug(f"Heatpump aan - 10 minutes above {feed}W grid in => go to boiler")
                return actief

            # Calculate solar production forecast
            today = datetime.utcnow()
            yesterday = today - timedelta(days=1)
            formatted_date = yesterday.strftime("%Y%m%d")
            yesterday_filename = f"{formatted_date}.txt"

            solar_production_forecast = self.solar_forecast.readfile(yesterday_filename)
            watt_today = 0
            if solar_production_forecast is not None:
                solar_production_forecast = solar_production_forecast['result']['watts']
                #self.logger.debug(f"Heatpump - production forecast: {solar_production_forecast}")

                today = datetime.now().strftime("%Y-%m-%d")
                for datetime_string, wattage in solar_production_forecast.items():
                    if datetime_string.startswith(today):
                        watt_today += wattage
            else:
                self.logger.debug(f"Heatpump - production forecast: No file found.. continuing without production forecast")

            self.logger.debug(f"Heatpump - watt_today: {watt_today}")

            # Calculate added hours based on average temperature and forecast
            weather_data = self.temp_handler.readfile(yesterday_filename)
            if weather_data is None:
                raise Exception('weather data of yesterday not found - exiting Heatpump')
            next_day_temperature, next_day_cloudcover = self.temp_handler.filter_next_day_data(weather_data)
            avg_temperature = self.temp_handler.calculate_avg_temperature(next_day_temperature)

            data = [
                (0, 7),
                (2, 8),
                (5, 10),
                (7, 12),
                (10, 14),
                (15, 18),
                (25, 12),
                (35, 12),
            ]
            amount_hours_chosen = next((added_hours for threshold, added_hours in data if avg_temperature < threshold), None)

            amount_added_hours_forecast = max(0, (watt_today - 9000) // 5000)
            self.logger.debug(f"Heatpump - Watt forecast: {watt_today} so added {amount_added_hours_forecast} hours")

            totalhours = amount_hours_chosen + amount_added_hours_forecast
            self.logger.debug(f"Heatpump - Avg T today(pred): {round(avg_temperature, 2)}° so {amount_hours_chosen} hours")
            day_ahead_hours_today = self.duurste_uren_handler.get_duurste_uren(totalhours)
            self.logger.debug(f"Heatpump - day_ahead_hours today (already chosen): {day_ahead_hours_today}")
            #
            # Assuming you're using a specific timezone, e.g., Europe/Brussels
            timezone = pytz.timezone("Europe/Brussels")

            # Get the current time in the local timezone
            now = datetime.now(timezone)

            # Add one hour to the current local time
            hour_plus_one = now.hour + 1

            # Apply the custom hour logic to handle "24" and no "hour 0"
            if hour_plus_one == 24:
                adjusted_hour = 24
            elif hour_plus_one == 0:
                adjusted_hour = 1
            else:
                adjusted_hour = hour_plus_one
            
            self.logger.debug(f"hour of day local +1 (adjusted): {adjusted_hour}")
                
            # Check if the adjusted hour is in the list of the most expensive hours
            if adjusted_hour in [int(datablock[1]) for datablock in day_ahead_hours_today]:
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
                    self.logger.debug("Solar boiler - Battery log file is empty.")
                    return False

                last_line = lines[-1].strip()
                timestamp_str, value = last_line.split(" - ")
                battery_value = float(value)
                time_last_line = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")

                # Check if battery value is recent
                if (datetime.now() - time_last_line) > timedelta(minutes=20):
                    self.logger.debug(f"Solar boiler - Battery value {battery_value} is not valid because it is too old.")
                    return False
                else:
                    self.logger.debug(f"Solar boiler - Battery value {battery_value} has correct time check.")

                # Check if battery value is between 95 and 97 or higher
                if battery_value > 97 or (self.check_pin_35_active(log_directory) and battery_value > 95):
                    self.logger.debug(f"Solar boiler - Battery value {battery_value} >95 or btw 92 en 97 => Solar boiler charging active")
                    return True
                else: 
                   self.logger.debug(f"Solar boiler - Battery not charged enough => solar boiler charging inactive")
                        
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
        
    def check_conditions_Bat(self):
        actief = True  # True means not running (system is off)
        log_directory = '/home/pi/Automation/ESunAutomation/logs'
        file_path = '/home/pi/Automation/ESunAutomation/logs/bat_states.txt'
        consumption_file = os.path.join(log_directory, "consumption_today.txt")

        try:
            self.logger.debug("BAT: Starting battery condition check.")

            # Reading battery log file
            self.logger.debug(f"BAT: Reading battery log file: {file_path}")
            with open(file_path, 'r') as file:
                lines = file.readlines()
                if not lines:
                    self.logger.debug("BAT: Battery log file is empty.")
                    return True  # No need to run

                last_line = lines[-1].strip()
                self.logger.debug(f"BAT: Last line in battery log: {last_line}")
                timestamp_str, value = last_line.split(" - ")
                battery_value = float(value.split()[0])
                time_last_line = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")

                # Check if battery value is recent
                if (datetime.now() - time_last_line) > timedelta(minutes=20):
                    self.logger.debug(f"BAT: Battery value {battery_value} is too old (last update: {time_last_line})")
                    return True  # Battery data is outdated, no need to run
                else:
                    self.logger.debug(f"BAT: Battery value {battery_value} is recent (last update: {time_last_line})")

                    # Check if battery value is below 30 or charging and below 35
                    if battery_value < 30:
                        self.logger.debug(f"BAT: Battery value {battery_value} < 30 => activate charge")
                        return False  # System should run to charge
                    elif self.check_pin_36_active(log_directory) and battery_value < 35:
                        self.logger.debug(f"BAT: Pin 36 active and battery value {battery_value} < 35 => continue charge")
                        return False  # Continue charging

        except FileNotFoundError as file_error:
            self.logger.error(f"BAT: File not found: {str(file_error)}")
            return True  # No file, no need to run
        except ValueError as value_error:
            self.logger.error(f"BAT: Value error: {str(value_error)}")
            return True  # No valid data, no need to run
        except Exception as e:
            self.logger.error(f"BAT: An error occurred while checking battery file: {str(e)}")
            return True  # Error occurred, stop running

        self.logger.debug("BAT: Battery value and pin check completed.")

        if self.check_pin_36_active(log_directory) and (battery_value > 95):
            self.logger.debug(f"BAT: Battery sufficiently charged: {battery_value} > 95, no charging needed.")
            return True  # System should not run
        elif battery_value > 90:
            self.logger.debug(f"BAT: Battery sufficiently loaded {battery_value}, no charging needed.")
            return True  # System should not run

        try:
            self.logger.debug("BAT: Proceeding to grid data and consumption forecast analysis.")
            
            # Read grid data
            grid_data = self.get_last_50_grid_data()
            self.logger.debug(f"BAT: Last grid data: {grid_data[-1]}")

            # Use local time for calculations
            local_timezone = pytz.timezone('Europe/Berlin')  # Adjust according to your local timezone
            today = datetime.now(local_timezone)
            self.logger.debug(f"BAT: Current local time: {today}")

            # Read solar production forecast
            yesterday = today - timedelta(days=1)
            formatted_date = yesterday.strftime("%Y%m%d")
            yesterday_filename = f"{formatted_date}.txt"
            self.logger.debug(f"BAT: Reading solar forecast from: {yesterday_filename}")
            solar_production_forecast = self.solar_forecast.readfile(yesterday_filename)

            # Initialize variables
            forecast_dict = {}
            consumption_data = []
            consumption_dict = {}

            # Reading consumption data
            self.logger.debug(f"BAT: Reading consumption data from file: {consumption_file}")
            with open(consumption_file, 'r') as file:
                for line in file:
                    timestamp_str, consumption_str = line.strip().split(" - ")
                    hour = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S").hour
                    consumption = int(float(consumption_str.split()[0]) * 1000)  # Convert kWh to Wh
                    consumption_data.append((hour, consumption))
                    consumption_dict[timestamp_str] = consumption

            # Convert battery value to Wh (assuming 100% = 10KWh)
            battery_forecast_value = battery_value * 100

            # Initialize cumulative deficit
            cumulative_deficit = 0
            critical_hour_found = False

            self.logger.debug("BAT: Generating forecast for each hour of the day.")
            for hour in range(today.hour, 24):  # Local hours
                forecast_time_str = f"{today.strftime('%Y-%m-%d')} {hour:02d}:00:00"
                consumption = next((c for h, c in consumption_data if h == hour), 0)
                production = solar_production_forecast.get('result', {}).get('watts', {}).get(forecast_time_str, 0)
                projected_battery_value = battery_forecast_value - consumption + production
                
                if projected_battery_value < 5000 and not critical_hour_found:
                    critical_hour_found = True
                    critical_hour = hour
                    self.logger.debug(f"BAT: Critical hour found at hour {hour}: Battery projected to drop below 5000 Wh.")

                projected_battery_value = min(10000, max(0, projected_battery_value))
                battery_forecast_value = projected_battery_value
                if battery_forecast_value < 5000:
                    cumulative_deficit += 5000 - battery_forecast_value

                if critical_hour_found and hour >= critical_hour:
                    break

            charge_rate_per_hour = 2000  # 2kWh per hour
            hours_needed_for_charging = int((cumulative_deficit + charge_rate_per_hour - 1) // charge_rate_per_hour)

            day_ahead_hours_today = self.duurste_uren_handler.get_duurste_uren(24)
            sorted_day_ahead_hours = sorted(day_ahead_hours_today, key=lambda x: float(x[2]))
            self.logger.debug(f"BAT: Sorted day ahead: {sorted_day_ahead_hours}")

            if hours_needed_for_charging > 0:
                if critical_hour <= today.hour:
                    critical_hour = 24  

                for hour_data in sorted_day_ahead_hours:
                    hour = int(hour_data[1])
                    forecast_time_str = f"{today.strftime('%Y-%m-%d')} {hour:02d}:00:00"

                    if today.hour <= hour < critical_hour:
                        self.locked_charging_hour = forecast_time_str
                        self.logger.debug(f"BAT: Selected and locked cheapest charging hour: {self.locked_charging_hour}")
                        actief = False
                        break

            if self.locked_charging_hour:
                current_hour = today.hour
                current_minute = today.minute
                locked_hour = int(self.locked_charging_hour[-8:-6])

                if current_hour == locked_hour or (current_hour == locked_hour and current_minute < 59):
                    self.logger.debug("BAT: In the selected charging hour. System is running.")
                    actief = False
                else:
                    self.logger.debug("BAT: Locked hour has passed, ensuring system is not running.")
                    actief = True

        except Exception as e:
            self.logger.error(f"BAT: An error occurred while checking conditions: {str(e)}")
            actief = True

        return actief



    def check_conditions_LBS(self, morning_hours=1, day_hours=2):
        self.logger.debug("LBS - Starting check_conditions_LBS")

        # Check if the Tesla conditions are active
        if self.check_conditions_Tesla():
            self.logger.debug("LBS - Solar boiler viavia conditions are active, so LBS will not be activated.")
            return False

        actief = False  # Initialize actief

        # Use local time for the current date
        today = datetime.now()
        self.logger.debug(f"LBS - Current local date and time: {today}")

        # Calculate yesterday's date for filename (if needed)
        yesterday = today - timedelta(days=1)
        #self.logger.debug(f"LBS - Calculated yesterday's date: {yesterday}")

        formatted_date = yesterday.strftime("%Y%m%d")
        #self.logger.debug(f"LBS - Formatted yesterday's date for filename: {formatted_date}")

        yesterday_filename = f"{formatted_date}.txt"
        #self.logger.debug(f"LBS - Yesterday's filename: {yesterday_filename}")

        # Assuming the solar production forecast file is in local time:
        solar_production_forecast = self.solar_forecast.readfile(yesterday_filename)

        watt_today = 0
        if solar_production_forecast is not None:
            solar_production_forecast = solar_production_forecast['result']['watts']
            #self.logger.debug(f"LBS - Solar production forecast data: {solar_production_forecast}")

            today_str = today.strftime("%Y-%m-%d")
            #self.logger.debug(f"LBS - Today's date string: {today_str}")

            for datetime_string, wattage in solar_production_forecast.items():
                if datetime_string.startswith(today_str):
                    watt_today += wattage
            self.logger.debug(f"LBS - Calculated total watt_today: {watt_today}")
        else:
            self.logger.debug("LBS - No solar production forecast file found, continuing without it.")

        self.logger.debug(f"LBS - Final watt_today value: {watt_today}")
        
        # Get the current day of the week
        current_day = datetime.today().weekday()

        # Set threshold based on weekday/weekend
        if current_day < 5:  # Weekdays (0 = Monday, ..., 4 = Friday)
            threshold = 10000
            self.logger.debug(f"LBS - Weekday detected. Threshold set to {threshold}")    
            
        else:  # Weekends (5 = Saturday, 6 = Sunday)
            threshold = 20000
            self.logger.debug(f"LBS - Weekend detected. Threshold set to {threshold}")
                
        # Check if watt_today is below the appropriate threshold
        if watt_today < threshold:
            self.logger.debug(f"LBS - watt_today is less than {threshold}, proceeding with hour selection.")
            
            # Retrieve the list of hours sorted by price or priority
            day_ahead_hours_today = self.duurste_uren_handler.get_duurste_uren(24)
            #self.logger.debug(f"LBS - Retrieved day ahead hours: {day_ahead_hours_today}")

            sorted_day_ahead_hours = sorted(day_ahead_hours_today, key=lambda x: float(x[2]))
            #self.logger.debug(f"LBS - Sorted day ahead hours by price: {sorted_day_ahead_hours}")

            selected_hours = []
            early_morning_hours = []
            daytime_hours = []

            # Parse the hour from index 1, which represents the local hour corresponding to the time slot
            for hour in sorted_day_ahead_hours:
                hour_of_day = int(hour[1])  # Hour of the day is at index 1
                if 0 <= hour_of_day < 6:
                    early_morning_hours.append(hour)
                elif 6 <= hour_of_day < 24:
                    daytime_hours.append(hour)
            
            #self.logger.debug(f"LBS - Collected early morning hours (00:00-06:00): {early_morning_hours}")
            #self.logger.debug(f"LBS - Collected daytime hours (06:00-24:00): {daytime_hours}")

            if len(early_morning_hours) >= morning_hours:
                selected_hours.extend(early_morning_hours[:morning_hours])
                self.logger.debug(f"LBS - Selected morning hours: {early_morning_hours[:morning_hours]}")
            else:
                self.logger.debug(f"LBS - Not enough early morning hours available, selected: {early_morning_hours}")

            if len(daytime_hours) >= day_hours:
                selected_hours.extend(daytime_hours[:day_hours])
                self.logger.debug(f"LBS - Selected daytime hours: {daytime_hours[:day_hours]}")
            else:
                self.logger.debug(f"LBS - Not enough daytime hours available, selected: {daytime_hours}")

            unique_selected_hours = list(set(tuple(hour) for hour in selected_hours))
            #self.logger.debug(f"LBS - Unique selected hours: {unique_selected_hours}")

            current_hour = today.hour + 1  # The day-ahead hour corresponds to the local time slot's end hour
            #self.logger.debug(f"LBS - Current local hour (adjusted to match day-ahead slot): {current_hour}")

            # Find the price for the current hour and log it
            current_hour_price = None
            for hour in day_ahead_hours_today:
                hour_of_day = int(hour[1])
                if current_hour == hour_of_day:
                    current_hour_price = hour[2]
                    break

            self.logger.debug(f"LBS - Price for the current hour {current_hour}: {current_hour_price}")

            # Check if the current hour matches any of the selected hours
            for hour in unique_selected_hours:
                hour_of_day = int(hour[1])
                if current_hour == hour_of_day:
                    self.logger.debug(f"LBS - Current hour {current_hour} matches selected hour {hour_of_day}. Activating LBS.")
                    actief = True
                    break
            else:
                self.logger.debug(f"LBS - Current hour {current_hour} does not match any selected hours. LBS will not be activated.")

        else:
            self.logger.debug(f"LBS - watt_today {watt_today} is more than {threshold}, LBS will not be activated.")

        self.logger.debug(f"LBS - Returning actief: {actief}")
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
            self.logger.error("An error occurred while activating relay_largeboiler: " + str(e))   
    
    def deactivate_relay_tesla(self):
        try:
            GPIO.output(self.relay_pin_tesla, GPIO.HIGH)
        except Exception as e:
            self.logger.error("An error occurred while deactivating relay_largeboiler: " + str(e))
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
    
    def activate_relay_lbs(self):
        try:
            GPIO.output(self.relay_pin_lbs, GPIO.LOW)
        except Exception as e:
            self.logger.error("An error occurred while activating relay_lbs: " + str(e))   
    def deactivate_relay_lbs(self):
        try:
            GPIO.output(self.relay_pin_lbs, GPIO.HIGH)
        except Exception as e:
            self.logger.error("An error occurred while deactivating relay_lbs: " + str(e))
    
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
                self.logger.debug(f"Large boiler: Pin {self.relay_pin_tesla} active (large boiler running on solar)")
                if str(self.OK_TO_SWITCH) == "True":
                    self.activate_relay_tesla()
            else:
                self.logger.debug(f"Large Boiler: Pin {self.relay_pin_tesla} not active (large boiler not running on solar)")
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
            
            if self.check_conditions_LBS():
                self.logger.debug(f"Lbs: Pin {self.relay_pin_lbs} active (solar boiler running from grid)")
                if str(self.OK_TO_SWITCH) == "True":
                    self.activate_relay_lbs()
            else:
                self.logger.debug(f"Lbs: Pin {self.relay_pin_lbs} not active (solar boiler not running from grid)")
                if str(self.OK_TO_SWITCH) == "True":
                    self.deactivate_relay_lbs()
            
            self.log_pin_state(self.relay_pin_heatpump, GPIO.input(self.relay_pin_heatpump))
            self.log_pin_state(self.relay_pin_boiler, GPIO.input(self.relay_pin_boiler))
            self.log_pin_state(self.relay_pin_vent, GPIO.input(self.relay_pin_vent))
            self.log_pin_state(self.relay_pin_bat, GPIO.input(self.relay_pin_bat))
            self.log_pin_state(self.relay_pin_tesla, GPIO.input(self.relay_pin_tesla))
            self.log_pin_state(self.relay_pin_lbs, GPIO.input(self.relay_pin_lbs))
        
        except KeyboardInterrupt:
            pass
        except Exception as e:
            self.logger.error(f"An error occurred while running the automation: {str(e)}")
