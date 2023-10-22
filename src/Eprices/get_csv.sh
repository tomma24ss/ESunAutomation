#!/bin/bash
LOG_DIR="/home/pi/Automation/ESunAutomation/logs/nextdaypriceslogs"
# Create the log directory if it doesn't exist
mkdir -p "$LOG_DIR"
# Get the current date
CURRENT_DATE=$(date +"%Y-%m-%d")
# Log file for the current day
LOG_FILE="$LOG_DIR/log_$CURRENT_DATE.log"
# Append a timestamp and log the script start
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

# Directory containing XML files
XML_DIR="/home/pi/Automation/ESunAutomation/src/Eprices/data"

# Find the most recent XML file in the directory
recent_xml_file=$(ls -t "$XML_DIR"/*.xml | head -1)

# Check if there are any XML files in the directory
if [ -z "$recent_xml_file" ]; then
echo "$TIMESTAMP - No XML files found in $XML_DIR." >> "$LOG_FILE"
  exit 1
fi

# CSV output file
CSV_DATA_DIR="/home/pi/Automation/ESunAutomation/src/Eprices/csvdata"
current_date=$(date +"%Y%m%d")  # Variable for the current date
CSV_OUTPUT_FILE="$CSV_DATA_DIR/prices_${current_date}.csv"

# Create or clear the CSV output file
echo "Date,Hour,Price" > "$CSV_OUTPUT_FILE"

while IFS= read -r line; do
  if [[ $line == *"<start>"* ]]; then
    date=$(echo "$line" | xmlstarlet sel -t -v "//start")
  elif [[ $line == *"<position>"* ]]; then
    hour=$(echo "$line" | xmlstarlet sel -t -v "//position")
  elif [[ $line == *"<price.amount>"* ]]; then
    price=$(echo "$line" | xmlstarlet sel -t -v "//price.amount")
    echo "$date,$hour,$price" >> "$CSV_OUTPUT_FILE"
  fi
done < "$recent_xml_file"

echo "$TIMESTAMP - CSV file generated" >> "$LOG_FILE"
