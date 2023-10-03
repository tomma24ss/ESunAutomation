import sqlite3
import datetime

class SolarDataHandler:
    def __init__(self, db_file):
        self.db_file = db_file
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

    def fetch_data_today(self):
        try:
            if not self.conn:
                if not self.connect():
                    return []

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

            return data

        except sqlite3.Error as e:
            print("SQLite error:", e)
            return []
        finally:
            self.disconnect()

    def get_last_data(self):
        try:
            if not self.conn:
                if not self.connect():
                    return None

            cursor = self.conn.cursor()

            # Replace 'vwspotdata' with your table name
            table_name = "vwspotdata"
            timestamp_column = "TimeStamp"
            # Construct the SQL query to select the last row
            query = f"SELECT * FROM {table_name} ORDER BY {timestamp_column} DESC LIMIT 1;"

            # Execute the query
            cursor.execute(query)

            # Fetch the last data record
            last_data = cursor.fetchone()

            return last_data

        except sqlite3.Error as e:
            print("SQLite error:", e)
            return None
        finally:
            self.disconnect()

if __name__ == "__main__":
    db_file = "../smadata/SBFspot.db"
    handler = SolarDataHandler(db_file)

    # Fetch today's data
    data_today = handler.fetch_data_today()
    for record in data_today:
        print(record)

    # Get the last data record
    last_data = handler.get_last_data()
    if last_data:
        print("Last Data Record:", last_data)
