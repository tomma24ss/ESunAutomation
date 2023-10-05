import sqlite3
import datetime
import os

class SolarDataHandler:
    def __init__(self, db_file, output_folder):
        self.db_file = db_file
        self.output_folder = output_folder
        self.conn = None

    def connect(self):
        try:
            # Connect to the SQLite database
            self.conn = sqlite3.connect(self.db_file)
            return True
        except sqlite3.Error as e:
            print("SQLite error:", e)
            return False

    def disconnect(self):
        # Close the database connection
        if self.conn:
            self.conn.close()

    def fetch_and_append_data_today(self):
        try:
            if not self.conn:
                if not self.connect():
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
                with open(output_file, 'a') as file:
                    for record in data:
                        file.write(','.join(map(str, record)) + '\n')

        except sqlite3.Error as e:
            print("SQLite error:", e)
        finally:
            self.disconnect()

if __name__ == "__main__":
    db_file = "/home/pi/smadata/SBFspot.db"
    output_folder = "./data"  # Change to the desired folder path
    handler = SolarDataHandler(db_file, output_folder)

    # Fetch today's data and append it to the file
    handler.fetch_and_append_data_today()
