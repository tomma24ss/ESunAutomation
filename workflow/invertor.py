import sqlite3                                                                                                                                                                          getData.py                                                                                                                                                                                    import sqlite3
import datetime

# Path to the SQLite database file
db_file = "../smadata/SBFspot.db"

def fetch_data_today():
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

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

        # Create a list to store all data records
        all_data = []

        # You can process and print the data here
        for row in data:
            all_data.append(row)

        return all_data

    except sqlite3.Error as e:
        print("SQLite error:", e)
    finally:
        # Close the database connection
        if conn:
            conn.close()

if __name__ == "__main__":
    data_today = fetch_data_today()
    for record in data_today:
        print(record)