# run.py 
from dotenv import load_dotenv
from src.solar_automation import SolarAutomation
import os

if __name__ == "__main__":
    load_dotenv()
    relay_pin_boiler = int(os.getenv("RELAY_PIN_BOILER"))
    db_file_path = os.getenv("DB_FILE_PATH")
    csv_file_path = os.getenv("CSV_FILE_PATH")
    vwspotdata_file_path = os.getenv("VWSPOTDATA_FILE_PATH")

    solar_automation = SolarAutomation(relay_pin_boiler, db_file_path, csv_file_path, vwspotdata_file_path)

    solar_automation.run()

    solar_automation.cleanup()
    
