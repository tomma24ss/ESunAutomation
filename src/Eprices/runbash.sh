#!/bin/bash
# Directory for log files
LOG_DIR="/home/pi/Automation/ESunAutomation/logs/nextdaypriceslogs"
# Create the log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Get the current date
CURRENT_DATE=$(date +"%Y-%m-%d")

# Log file for the current day
LOG_FILE="$LOG_DIR/log_$CURRENT_DATE.log"

# Append a timestamp and log the script start
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

echo "$TIMESTAMP - Starting workflow" >> "$LOG_FILE"
/home/pi/Automation/ESunAutomation/src/Eprices/get_electricity_prices.sh
/home/pi/Automation/ESunAutomation/src/Eprices/get_csv.sh
echo "$TIMESTAMP - Workflow Done" >> "$LOG_FILE"

