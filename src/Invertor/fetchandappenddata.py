import sqlite3
import datetime
import os
from dotenv import load_dotenv
import sys
sys.path.append("/home/pi/Automation")
from ESunAutomation.src.Logger.logger import MyLogger

class SolarDataHandler:
    def __init__(self, db_file, output_folder):
        self.db_file = db_file
        self.output_folder = output_folder
        self.conn = None
        self.logger = MyLogger()

    def connect(self):
        try:
            # Connect to the SQLite database
            self.conn = sqlite3.connect(self.db_file)
            self.logger.debug("Connected to the database.")
            return True
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error:{e}")
            return False

    def disconnect(self):
        # Close the database connection
        if self.conn:
            self.conn.close()
            self.logger.debug("Disconnected from the database.")

    def fetch_and_append_data_today(self):
        try:
            if not self.conn:
                if not self.connect():
                    self.logger.error("Failed to connect to the database. Cannot fetch data.")
                    return

            cursor = self.conn.cursor()

            # Replace 'vwspotdata' with your table name and 'timestamp_column' with the actual timestamp column name
            table_name = "vwspotdata"
            timestamp_column = "TimeStamp"

            # Get today's date in the format "YYYY-MM-DD"
            today_date = datetime.date.today()

            # Construct the SQL query to select rows for today's date
            query = f"SELECT * FROM {table_name} WHERE DATE({timestamp_column}) = ?;"

            # Execute the query with the date as a parameter
            cursor.execute(query, (today_date,))

            # Fetch all the data
            data = cursor.fetchall()

            if data:
                if not os.path.exists(self.output_folder):
                    os.makedirs(self.output_folder)

                # Construct the output file path with the current date
                output_file = os.path.join(self.output_folder, f"{today_date}.txt")

                # Append data to the file
                with open(output_file, 'w') as file:
                    for record in data:
                        file.write(','.join(map(str, record)) + '\n')

                self.logger.debug(f"Data for {today_date} appended to {output_file}")
            else:
                self.logger.debug(f"No data found for {today_date}.")

        except sqlite3.Error as e:
            print("SQLite error:", e)
            self.logger.error(f"SQLite error:{e}")
        finally:
            self.disconnect()

if __name__ == "__main__":
    load_dotenv() # Load environment variables from .env file
    db_file = os.getenv("DB_FILE_PATH")
    output_folder = os.getenv("VWSPOTDATA_FILE_PATH")
    handler = SolarDataHandler(db_file, output_folder)

    # Fetch today's data and append it to the file
    handler.fetch_and_append_data_today()
