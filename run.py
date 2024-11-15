# run.py 
from dotenv import load_dotenv
from src.automation import SolarBoilerAutomation
import os

if __name__ == "__main__":
    load_dotenv() # Load environment variables from .env file
    relay_pin_heatpump = int(os.getenv("RELAY_PIN_HEATPUMP"))
    relay_pin_boiler = int(os.getenv("RELAY_PIN_BOILER"))
    relay_pin_vent= int(os.getenv("RELAY_PIN_VENT"))
    relay_pin_bat= int(os.getenv("RELAY_PIN_BAT"))
    relay_pin_tesla= int(os.getenv("RELAY_PIN_TESLA"))
    relay_pin_lbs= int(os.getenv("RELAY_PIN_LBS"))
    db_file_path = os.getenv("DB_FILE_PATH")
    csv_file_path = os.getenv("CSV_FILE_PATH")
    vwspotdata_file_path = os.getenv("VWSPOTDATA_FILE_PATH")
    griddata_file_path = os.getenv("GRIDDATA_FILE_PATH")
    weatherdata_file_path  = os.getenv("WEATHERDATA_FILE_PATH")
    productionforecastdata_file_path = os.getenv("PRODUCTIONFORECASTDATA_FILE_PATH")
    AANTAL_DUURSTE_UREN_6_24 = os.getenv("AANTAL_DUURSTE_UREN_6_24")
    AANTAL_DUURSTE_UREN_0_6 = os.getenv("AANTAL_DUURSTE_UREN_0_6")
    HEATPUMP_TOGGLE_WATTAGE = os.getenv("HEATPUMP_TOGGLE_WATTAGE")
    BOILER_TOGGLE_WATTAGE_HIGHFEED = os.getenv("BOILER_TOGGLE_WATTAGE_HIGHFEED")
    BOILER_TOGGLE_WATTAGE_LOWFEED = os.getenv("BOILER_TOGGLE_WATTAGE_LOWFEED")
    OK_TO_SWITCH = os.getenv("OK_TO_SWITCH")

    solar_automation = SolarBoilerAutomation(
    relay_pin_heatpump, relay_pin_boiler, relay_pin_vent, relay_pin_bat, 
    relay_pin_tesla, relay_pin_lbs, db_file_path, csv_file_path, 
    vwspotdata_file_path, griddata_file_path, weatherdata_file_path, 
    productionforecastdata_file_path, AANTAL_DUURSTE_UREN_6_24, 
    AANTAL_DUURSTE_UREN_0_6, OK_TO_SWITCH, HEATPUMP_TOGGLE_WATTAGE, 
    BOILER_TOGGLE_WATTAGE_HIGHFEED, BOILER_TOGGLE_WATTAGE_LOWFEED
    )   

    solar_automation.run()

    #solar_automation.cleanup()
    
