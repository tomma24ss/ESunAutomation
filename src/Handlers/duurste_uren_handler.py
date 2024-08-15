# Import the necessary libraries if they are not already imported
import csv, os
from datetime import datetime, timedelta

class DuursteUrenHandler:
    def __init__(self, csv_file_dir, AANTAL_DUURSTE_UREN_6_24, AANTAL_DUURSTE_UREN_0_6, logger):
        self.csv_file_dir = csv_file_dir
        self.AANTAL_DUURSTE_UREN_6_24 = AANTAL_DUURSTE_UREN_6_24
        self.AANTAL_DUURSTE_UREN_0_6 = AANTAL_DUURSTE_UREN_0_6
        self.logger = logger

    def getlatestfile(self):
      # Get a list of files in the directory
      dic = self.csv_file_dir
      files = [os.path.join(dic, filename) for filename in os.listdir(dic)]
      # Filter out directories and get the most recently modified file
      latest_file = max(files, key=os.path.getctime)
      return latest_file
    def getyesterdayfile(self):
        # Calculate the date for yesterday
        yesterday = datetime.utcnow() - timedelta(days=1)
        formatted_date = yesterday.strftime("%Y%m%d")
        yesterday_filename = f"prices_{formatted_date}.csv"

        # Check if the file for yesterday exists and contains data
        yesterday_file_path = os.path.join(self.csv_file_dir, yesterday_filename)
        if os.path.exists(yesterday_file_path) and os.path.getsize(yesterday_file_path) > 50: #20 bc headers will be always present
            return yesterday_file_path
        else:
            raise FileNotFoundError(f'No {yesterday_filename} file found for yesterdays date')
            
    def is_duurste_uren(self):
        try:
            alle_uren = self.get_alle_uren()
            start_time = '07'
            end_time = '24'
            end_time_00 = '00'
            hours_07_to_24 = []
            hours_00_to_07 = []
            for row in alle_uren:
                time = row[1].zfill(2)  # Ensure two-digit format with leading zeros
                if start_time <= time <= end_time:
                    hours_07_to_24.append(row)
                if end_time_00 <= time < start_time:
                    hours_00_to_07.append(row)
            hours_07_to_24.sort(key=lambda x: float(x[2]), reverse=True)
            hours_00_to_07.sort(key=lambda x: float(x[2]), reverse=True)

            duurste_uren = hours_07_to_24[0:int(self.AANTAL_DUURSTE_UREN_6_24)] + hours_00_to_07[0:int(self.AANTAL_DUURSTE_UREN_0_6)]
            duurste_uren.sort(key=lambda x: float(x[1]), reverse=True)
            self.logger.debug("Gekozen uren: " + str(duurste_uren))
            gekozen_uren_met_prijs = [{'hour': row[1], 'price': row[2]} for row in duurste_uren]
            self.logger.debug("Gekozen Uren met prijs: " + str(gekozen_uren_met_prijs))

            hours_array = [int(row[1]) for row in duurste_uren]
            now = int(datetime.utcnow().strftime("%H"))
            self.logger.debug(f"uur {now}")
            return now in hours_array
         
        except Exception as e:
            self.logger.error("An error occurred while checking isduurste uren: " + str(e))
            return False

    def get_alle_uren(self): #fout  in 24u ? sort 
        try:
            alle_uren = []
            with open(os.path.join(self.csv_file_dir, self.getyesterdayfile()), newline='') as csvfile:
                reader = csv.reader(csvfile, delimiter=',', quotechar='"')
                next(reader, None)  # skip the headers
                for row in reader:
                    alle_uren.append(row)
            alle_uren.sort(key=lambda x: float(x[1]), reverse=False)  # fout ? 24 zit na 1   
            return alle_uren
        except Exception as e:
            self.logger.error("An error occurred while getting duurste uren: " + str(e))
            return []
    def get_duurste_uren(self, amount_hours):
        alleuren = self.get_alle_uren()
        sorted_uren = sorted(alleuren, key=lambda x: float(x[2]), reverse=True)
        most_expensive_hours = sorted_uren[:amount_hours]

        return most_expensive_hours
    def best_uur_wachten(self, hoursneeded):
        try:
            uur_prijs = [{'hour': row[1], 'price':row[2]} for row in self.get_alle_uren()]
            print(uur_prijs)
            hournow = datetime.utcnow().strftime("%H") + 2
            nexthours = [row['hour'] for row in uur_prijs if row['hour'] > hournow]
            price_now = uur_prijs[int(hournow)]['price']
            amount_nexthours_cheaper = 0
            for hour in nexthours:
                price_next = uur_prijs[int(hour)]['price']
                if price_now > price_next:
                    amount_nexthours_cheaper += 1
                else :
                    break
                
            if amount_nexthours_cheaper >= hoursneeded:
                return True
            else:
                return False
        except Exception as e:
            self.logger.error("An error occurred while checking isduurste uren: " + str(e))
            return False  
