import os
import RPi.GPIO as GPIO
import math
from datetime import datetime, timedelta
import csv,os,time, subprocess
from src.Invertor.datahandler import DataHandler
from src.Logger.logger import MyLogger
from src.Handlers.duurste_uren_handler import DuursteUrenHandler
from src.SolarForecast.sunsetconditions import SunsetConditions
from src.SolarForecast.solar_forecast import SolarProductionForecast
from src.Weather.gettemp import Temp

class SolarBoilerAutomation:
    def __init__(self, relay_pin_heatpump,relay_pin_boiler, relay_pin_vent, relay_pin_bat, db_file, csv_file_path, vwspotdata_file_path,griddata_file_path, weatherdata_file_path, productionforecastdata_file_path, AANTAL_DUURSTE_UREN_6_24=13, AANTAL_DUURSTE_UREN_0_6=3, OK_TO_SWITCH=False, HEATPUMP_TOGGLE_WATTAGE=300, BOILER_TOGGLE_WATTAGE_HIGHFEED=1500, BOILER_TOGGLE_WATTAGE_LOWFEED=300):
        self.relay_pin_heatpump = relay_pin_heatpump
        self.relay_pin_boiler = relay_pin_boiler
        self.relay_pin_vent = relay_pin_vent
        self.relay_pin_bat = relay_pin_bat
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
        GPIO.setup(self.relay_pin_vent, GPIO.OUT)
        GPIO.setup(self.relay_pin_bat, GPIO.OUT)

        self.temp_handler = Temp(latitude, longitude, weatherdata_file_path)
        self.solar_forecast = SolarProductionForecast(latitude, longitude, inclination, azimuth, capacity, productionforecastdata_file_path)
        self.data_handler = DataHandler(vwspotdata_file_path)
        self.logger = MyLogger()
        self.duurste_uren_handler = DuursteUrenHandler(csv_file_path, AANTAL_DUURSTE_UREN_6_24, AANTAL_DUURSTE_UREN_0_6, self.logger)
        self.sunsetconditions = SunsetConditions(productionforecastdata_file_path, self.logger)
    def log_pin_state(self, pin, state):
        # Prepare the filename
        filename = "pin_states.txt"
        # Get the current date and time
        now = datetime.datetime.now()
        formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")
        # Prepare the message with the state of the relay pin
        message = f"{formatted_time} - Pin {pin}: {state}\n"
        # Write to the file
        with open(filename, 'a') as file:
            file.write(message)
        self.logger.debug(f"Pin {pin} state ({state}) logged to file.")
    def check_conditions_Heatpump(self):
        actief = True   
        try:
            # Check condition 1: Grid injection < 250W for 10+ minutes
            wattages = self.data_handler.read_lastdata_txt()
            last_10_wattages = wattages[:10]  # Get the last 10 rows (representing 10 minutes)
            self.logger.debug("Heatpump - Last 10 minutes w: " + str(last_10_wattages))
            # Convert the wattage values to floats
            wattage_values = [float(w) for w in last_10_wattages] if last_10_wattages else []
            #self.logger.debug("Heatpump - Avg W for 10 minutes: " + str(sum(wattage_values) / len(wattage_values) ))
            if all(wattage < self.HEATPUMP_TOGGLE_WATTAGE for wattage in wattage_values):
                self.logger.debug(f"Heatpump - last 10 minutes under {self.HEATPUMP_TOGGLE_WATTAGE}W => go to next heatpump check")
                actief = True
            elif all(wattage > self.HEATPUMP_TOGGLE_WATTAGE for wattage in wattage_values):
                self.logger.debug(f"Heatpump - last 10 minutes above {self.HEATPUMP_TOGGLE_WATTAGE}W => set and go to boiler")
                actief = False
                return actief

            #grid
            feed = 500
            # until the grid in is higher than 1000
            grid_data = self.get_last_50_grid_data()  # Replace with the actual method to get inverter production
            consecutive_low_minutes_feed = 0
            consecutive_high_minutes_feed = 0
            lastdata = grid_data[-1]
            grid_in_now = float(lastdata['gridin']) if lastdata['gridin'] != 'N/A' else 0
            grid_out_now = float(lastdata['gridout']) if lastdata['gridout'] != 'N/A' else 0
            self.logger.debug("Heatpump - Grid in: " + str(grid_in_now) + " Grid out: " + str(grid_out_now))

            for data in grid_data[-10:]:
                grid_in = float(data['gridin']) if data['gridin'] != 'N/A' else 0
                #grid_out = float(data['gridout']) if data['gridout'] != 'N/A' else 0
                if grid_in <= feed:
                    consecutive_low_minutes_feed += 1
                    consecutive_high_minutes_feed = 0
                else:
                    consecutive_low_minutes_feed = 0
                    consecutive_high_minutes_feed += 1
                    #self.logger.debug("Boiler - Consecutive high minutes: " + str(consecutive_high_minutes))
                # if consecutive_low_minutes_highfeed >= 1 or consecutive_high_minutes_highfeed >= 1:
                #     break  # Exit the loop if both conditions are met
            self.logger.debug(f"Heatpump - gridin minutes above {feed}w : {consecutive_high_minutes_feed}")
            self.logger.debug(f"Heatpump - gridin minutes below {feed}w : {consecutive_low_minutes_feed}")
            
            if consecutive_low_minutes_feed >= 10 : 
                actief = True
                self.logger.debug(f"Heatpump uit - 10 minutes below {feed}W grid in => go to time check")
            if consecutive_high_minutes_feed >= 10:
                actief = False
                self.logger.debug(f"Heatpump aan - 10 minutes above {feed}W grid in => go to boiler")
                return actief  
            #solarforecast
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
                # Iterate over the items in the 'watts' dictionary
                for datetime_string, wattage in solar_production_forecast.items():
                    # Check if the date in the datetime_string matches today's date
                    if datetime_string.startswith(today):
                        watt_today += wattage
                        
            else:
                self.logger.debug(f"Heatpump - production forecast: No file found.. continuing without production forecast")
            
            self.logger.debug(f"Heatpump - watt_today: {watt_today}")

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
                # if consecutive_low_minutes_highfeed >= 1 or consecutive_high_minutes_highfeed >= 1:
                #     break  # Exit the loop if both conditions are met
            self.logger.debug(f"Boiler - gridin minutes above {highfeed}w : {consecutive_high_minutes_highfeed}")
            self.logger.debug(f"Boiler - gridin minutes above {lowfeed}w : {consecutive_high_minutes_lowfeed}")
            self.logger.debug(f"Boiler - gridin minutes below {lowfeed}w : {consecutive_low_minutes_lowfeed}")
            
            if consecutive_low_minutes_lowfeed >= 10 and boileraan: #boiler uit -> kijken naar uren
                actief = True
                self.logger.debug(f"Boiler uit - 10 minutes below {lowfeed}W grid in")
            if consecutive_high_minutes_lowfeed >= 10 and boileraan:
                actief = False
                self.logger.debug(f"Boiler aan met uren - 10 minutes above {lowfeed}W grid in") #boiler aan -> niet kijken naar uren
                return actief 
            if consecutive_high_minutes_highfeed >= 10 and not boileraan:
                actief = False
                self.logger.debug(f"Boiler aan geen uren - 10 minutes above {highfeed}W grid in") #boiler aan -> niet kijken naar uren
                return actief   

            # Check condition 2: Duurste uren
            if(self.duurste_uren_handler.is_duurste_uren()):
                actief = True #papa: dit hier bijgezet
                self.logger.debug("Boiler - Zit in duurste uren met 2 uur correctie") 
            
            else:
                actief = False
                self.logger.debug("Boiler - Zit niet in duurste uren met 2 uur correctie") #boiler aan
                self.duurste_uren_handler 


        except Exception as e:
            self.logger.error("Boiler - An error occurred while checking conditions: " + str(e))
            actief = True

        return actief
    
    def check_conditions_vent(self):
        actief = True
        try:
            # Check condition 1: Grid injection < 600W for 10+ minutes
            wattages = self.data_handler.read_lastdata_txt()
            last_10_wattages = wattages[:10]  # Get the last 10 rows (representing 10 minutes)
            self.logger.debug("Vent - Last 10 minutes w: " + str(last_10_wattages))
            # Convert the wattage values to floats
            wattage_values = [float(w) for w in last_10_wattages] if last_10_wattages else []
            #self.logger.debug("Vent - Avg W for 10 minutes: " + str(sum(wattage_values) / len(wattage_values) ))
            if all(wattage < self.HEATPUMP_TOGGLE_WATTAGE for wattage in wattage_values):
                self.logger.debug(f"Vent - last 10 minutes under {self.HEATPUMP_TOGGLE_WATTAGE}W => go to next check")
                actief = True
            elif all(wattage > self.HEATPUMP_TOGGLE_WATTAGE for wattage in wattage_values):
                self.logger.debug(f"Vent - last 10 minutes above {self.HEATPUMP_TOGGLE_WATTAGE}W => OK done ")
                actief = False
                return actief

            #grid
            feed = 250
            # until the grid in is higher than 1000
            grid_data = self.get_last_50_grid_data()  # Replace with the actual method to get inverter production
            consecutive_low_minutes_feed = 0
            consecutive_high_minutes_feed = 0
            lastdata = grid_data[-1]
            grid_in_now = float(lastdata['gridin']) if lastdata['gridin'] != 'N/A' else 0
            grid_out_now = float(lastdata['gridout']) if lastdata['gridout'] != 'N/A' else 0
            self.logger.debug("Vent - Grid in: " + str(grid_in_now) + " Grid out: " + str(grid_out_now))

            for data in grid_data[-10:]:
                grid_in = float(data['gridin']) if data['gridin'] != 'N/A' else 0
                #grid_out = float(data['gridout']) if data['gridout'] != 'N/A' else 0
                if grid_in <= feed:
                    consecutive_low_minutes_feed += 1
                    consecutive_high_minutes_feed = 0
                else:
                    consecutive_low_minutes_feed = 0
                    consecutive_high_minutes_feed += 1
                    #self.logger.debug("Boiler - Consecutive high minutes: " + str(consecutive_high_minutes))
                # if consecutive_low_minutes_highfeed >= 1 or consecutive_high_minutes_highfeed >= 1:
                #     break  # Exit the loop if both conditions are met
            self.logger.debug(f"Vent - gridin minutes above {feed}w : {consecutive_high_minutes_feed}")
            self.logger.debug(f"Vent - gridin minutes below {feed}w : {consecutive_low_minutes_feed}")
            
            if consecutive_low_minutes_feed >= 10 : 
                actief = True
                self.logger.debug(f"Vent uit - 10 minutes below {feed}W grid in => go to time check")
            if consecutive_high_minutes_feed >= 10:
                actief = False
                self.logger.debug(f"Vent aan - 10 minutes above {feed}W grid in => done")
                return actief  
            #solarforecast
            today = datetime.utcnow()
            yesterday = today - timedelta(days=1)
            formatted_date = yesterday.strftime("%Y%m%d")
            yesterday_filename = f"{formatted_date}.txt"

            solar_production_forecast = self.solar_forecast.readfile(yesterday_filename)
            
            watt_today = 0
            if solar_production_forecast is not None:
                solar_production_forecast = solar_production_forecast['result']['watts']
                self.logger.debug(f"Vent - production forecast: {solar_production_forecast}")
            
                today = datetime.now().strftime("%Y-%m-%d")
                #self.logger.debug(f"Heatpump - today: {today}")
            
                # Iterate over the items in the 'watts' dictionary
                for datetime_string, wattage in solar_production_forecast.items():
                
                # Check if the date in the datetime_string matches today's date
                    if datetime_string.startswith(today):
                        watt_today += wattage
                        
            else:
                self.logger.debug(f"Vent - production forecast: No file found.. continuing without production forecast")
            
            self.logger.debug(f"Vent - watt_today: {watt_today}")

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
                (0, 4),
                (2, 4),
                (5, 4),
                (7, 8),
                (10, 12),
                (15, 12),
                (25, 12),
                (35, 12),
            ]
            amount_hours_chosen = calculate_added_hours(avg_temperature, data)
                       
            amount_added_hours_forecast = math.floor((watt_today - 9000) / 30000)
            self.logger.debug(f"Vent - Watt forecast: {watt_today} so added {amount_added_hours_forecast} hours")

            totalhours = amount_hours_chosen + amount_added_hours_forecast
            self.logger.debug(f"Vent - Avg T today(pred): {round(avg_temperature, 2)}° so {amount_hours_chosen} hours")
            day_ahead_hours_today = self.duurste_uren_handler.get_duurste_uren(totalhours) 
            self.logger.debug(f"Vent - Total hours + forecast: {totalhours}")
            self.logger.debug(f"Vent - day_ahead_hours today (already chosen): {day_ahead_hours_today}")
            self.logger.debug(f"hour of day now(utc) + 2uur correctie: {datetime.utcnow().hour + 2}")
           
            if((datetime.utcnow().hour + 2) in [int(datablock[1]) for datablock in day_ahead_hours_today]):
                self.logger.debug("Vent - Zit in duurste uren met 2 uur correctie")
                actief = True
            else: 
                actief = False
                self.logger.debug("Vent - Zit niet in duurste uren met 2 uur correctie")

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
   
    def check_conditions_Bat(self):
        actief = True   
        try:
            #grid
            feed = 4000
            # until the grid in is higher than 4000
            grid_data = self.get_last_50_grid_data()  # Replace with the actual method to get inverter production
            consecutive_low_minutes_feed = 0
            consecutive_high_minutes_feed = 0
            lastdata = grid_data[-1]
            grid_in_now = float(lastdata['gridin']) if lastdata['gridin'] != 'N/A' else 0
            grid_out_now = float(lastdata['gridout']) if lastdata['gridout'] != 'N/A' else 0
            self.logger.debug("Bat - Grid in: " + str(grid_in_now) + " Grid out: " + str(grid_out_now))

            for data in grid_data[-10:]:
                grid_in = float(data['gridin']) if data['gridin'] != 'N/A' else 0
                #grid_out = float(data['gridout']) if data['gridout'] != 'N/A' else 0
                if grid_in <= feed:
                    consecutive_low_minutes_feed += 1
                    consecutive_high_minutes_feed = 0
                else:
                    consecutive_low_minutes_feed = 0
                    consecutive_high_minutes_feed += 1
                    #self.logger.debug("Bat - Consecutive high minutes: " + str(consecutive_high_minutes))
                # if consecutive_low_minutes_highfeed >= 1 or consecutive_high_minutes_highfeed >= 1:
                #     break  # Exit the loop if both conditions are met
            self.logger.debug(f"Bat - gridin minutes above {feed}w : {consecutive_high_minutes_feed}")
            self.logger.debug(f"Bat - gridin minutes below {feed}w : {consecutive_low_minutes_feed}")
            
            if consecutive_low_minutes_feed >= 10 : 
                actief = True
                self.logger.debug(f"Bat uit - 10 minutes below {feed}W grid in => go to time check")
            if consecutive_high_minutes_feed >= 10:
                actief = False
                self.logger.debug(f"Bat aan - 10 minutes above {feed}W grid in => set and stop")
                return actief  
            #solarforecast
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
                # Iterate over the items in the 'watts' dictionary
                for datetime_string, wattage in solar_production_forecast.items():
                    # Check if the date in the datetime_string matches today's date
                    if datetime_string.startswith(today):
                        watt_today += wattage
                        
            else:
                self.logger.debug(f"Bat - production forecast: No file found.. continuing without production forecast")
            
            self.logger.debug(f"Bat - watt_today: {watt_today}")

            #weather
            weather_data = self.temp_handler.readfile(yesterday_filename)
            if(weather_data is None): raise Exception('weather data of yesterday not found - exciting Bat')
            next_day_temperature, next_day_cloudcover = self.temp_handler.filter_next_day_data(weather_data)
            avg_temperature = self.temp_handler.calculate_avg_temperature(next_day_temperature)
            def calculate_added_hours(avg_temperature, threshold_data):
                for threshold, added_hours in threshold_data:
                    if avg_temperature < threshold:
                        return added_hours
                return None  # Return None if the temperature is higher than all thresholds
            data = [
                (0, 18),
                (2, 18),
                (5, 18),
                (7, 18),
                (10, 18),
                (15, 18),
                (25, 18),
                (35, 18),
            ]
            amount_hours_chosen = calculate_added_hours(avg_temperature, data)
                       
            amount_added_hours_forecast = math.floor((watt_today - 1000) / 4000)
            self.logger.debug(f"Bat - Watt forecast: {watt_today} so added {amount_added_hours_forecast} hours")

            totalhours = amount_hours_chosen + amount_added_hours_forecast
            self.logger.debug(f"Bat - Avg T today(pred): {round(avg_temperature, 2)}° so {amount_hours_chosen} hours")
            day_ahead_hours_today = self.duurste_uren_handler.get_duurste_uren(totalhours) 
            self.logger.debug(f"Bat - Total hours + forecast: {totalhours}")
            self.logger.debug(f"Bat - day_ahead_hours today (already chosen): {day_ahead_hours_today}")
            self.logger.debug(f"hour of day now(utc) + 2uur correctie: {datetime.utcnow().hour + 2}")
           
            if((datetime.utcnow().hour + 2) in [int(datablock[1]) for datablock in day_ahead_hours_today]):
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
    def activate_relay_vent(self):
        try:
            GPIO.output(self.relay_pin_vent, GPIO.LOW)  # Activate the relay
        except Exception as e:
            self.logger.error("An error occurred while activating relay_vent: " + str(e))   
    def deactivate_relay_vent(self):
        try:
            GPIO.output(self.relay_pin_vent, GPIO.HIGH)  # Deactivate the relay
        except Exception as e:
            self.logger.error("An error occurred while deactivating relay_vent: " + str(e))
    def activate_relay_bat(self):
        try:
            GPIO.output(self.relay_pin_bat, GPIO.LOW)  # Activate the relay
        except Exception as e:
            self.logger.error("An error occurred while activating relay_bat: " + str(e))   
    def deactivate_relay_bat(self):
        try:
            GPIO.output(self.relay_pin_bat, GPIO.HIGH)  # Deactivate the relay
        except Exception as e:
            self.logger.error("An error occurred while deactivating relay_bat: " + str(e))

    def run(self):  
        try:
            self.logger.debug("Checking conditions at minute: " + str(datetime.utcnow()))
            self.logger.debug(f"OK_TO_SWITCH:" + str(self.OK_TO_SWITCH))
            if self.check_conditions_Heatpump(): #
                self.logger.debug("Heatpump: Pin {} actief (niet draaien)".format(self.relay_pin_heatpump))
                if str(self.OK_TO_SWITCH) == "True":
                    self.activate_relay_heatpump()
                    self.logger.debug("Heatpump: Pin {} aan (niet draaien)".format(self.relay_pin_heatpump)) #heatpump pin aan dus moet niet draaien
            else:
                self.logger.debug("Heatpump: Pin {} niet actief (draaien)".format(self.relay_pin_heatpump))
                if str(self.OK_TO_SWITCH) == "True":
                    self.deactivate_relay_heatpump()
                    self.logger.debug("Heatpump: Pin {} uit (draaien)".format(self.relay_pin_heatpump)) #heatpump pin uit dus moet draaien    

            if self.check_conditions_boiler():
                self.logger.debug("Boiler: Pin {} actief (niet draaien)".format(self.relay_pin_boiler))
                if str(self.OK_TO_SWITCH) == "True":
                    self.activate_relay_boiler()
                    self.logger.debug("Boiler: Pin {} aan (niet  draaien)".format(self.relay_pin_boiler)) #boiler pin aan dus moet niet draaien
            else:
                self.logger.debug("Boiler: Pin {} niet actief (draaien)".format(self.relay_pin_boiler))
                if str(self.OK_TO_SWITCH) == "True":
                    self.deactivate_relay_boiler()
                    self.logger.debug("Boiler: Pin {} uit (draaien)".format(self.relay_pin_boiler))  #boiler pin uit dus moet draaien
                    
            if self.check_conditions_vent():
                self.logger.debug("Vent: Pin {} actief (niet draaien)".format(self.relay_pin_vent))
                if str(self.OK_TO_SWITCH) == "True":
                    self.activate_relay_vent()
                    self.logger.debug("Vent: Pin {} aan (niet  draaien)".format(self.relay_pin_vent)) #vent pin aan dus moet niet draaien
            else:
                self.logger.debug("Vent: Pin {} niet actief (draaien)".format(self.relay_pin_vent))
                if str(self.OK_TO_SWITCH) == "True":
                    self.deactivate_relay_vent()
                    self.logger.debug("Vent: Pin {} uit (draaien)".format(self.relay_pin_vent))  #vent pin uit dus moet draaien
            
            if self.check_conditions_Bat(): #
                self.logger.debug("Bat: Pin {} actief (niet draaien)".format(self.relay_pin_bat))
                if str(self.OK_TO_SWITCH) == "True":
                    self.activate_relay_bat()
                    self.logger.debug("Bat: Pin {} aan (niet draaien)".format(self.relay_pin_bat)) #bat pin aan dus moet niet draaien
            else:
                self.logger.debug("Bat: Pin {} niet actief (draaien)".format(self.relay_pin_bat))
                if str(self.OK_TO_SWITCH) == "True":
                    self.deactivate_relay_bat()
                    self.logger.debug("Bat: Pin {} uit (draaien)".format(self.relay_pin_bat)) #bat pin uit dus moet draaien
                    
            self.log_pin_state(self.relay_pin_bat, GPIO.input(self.relay_pin_bat))
        except KeyboardInterrupt:
            pass
        except Exception as e:
            self.logger.error("An error occurred while running the automation: " + str(e))
