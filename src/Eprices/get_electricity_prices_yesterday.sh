#!/bin/bash
LOG_DIR="/home/pi/Automation/ESunAutomation/logs/nextdaypriceslogs"
# Create the log directory if it doesn't exist
mkdir -p "$LOG_DIR"
# Get the current date
CURRENT_DATE=$(date +"%Y-%m-%d")
# Log file for the current day
LOG_FILE="$LOG_DIR/log_$CURRENT_DATE.log"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

# API URL and token
API_URL="https://web-api.tp.entsoe.eu"
TOKEN="c9de6ed7-5c65-42f1-8471-e85a41f1c4bd"

# Data directory
DATA_DIR="/home/pi/Automation/ESunAutomation/src/Eprices/data"

get_day_ahead_prices() {
    local current_date=$(date +"%Y%m%d")
    local tomorrow_date=$(date -d "+1 day" +"%Y%m%d")
    local yesterday_date=$(date -d "-1 day" +"%Y%m%d")
    local output_file="$DATA_DIR/day_ahead_prices_${yesterday_date}.xml"
    local api_endpoint="/api?securityToken=$TOKEN&documentType=A44&in_Domain=10YBE----------2&out_Domain=10YBE----------2&periodStart=${current_date}0000&periodEnd=${current_date}2300"
    # Make the API request using cURL and save the output to the file
    curl -s "$API_URL$api_endpoint" -o "$output_file"

    # Check if the request was successful (HTTP status code 200)
    if [ $? -eq 0 ]; then
        echo "$TIMESTAMP - Day Ahead Prices data for tomorrow fetched and saved to $output_file." >> "$LOG_FILE"
    else
        echo "$TIMESTAMP - Error: Failed to fetch Day Ahead Prices data for tomorrow from the API." >> "$LOG_FILE"
    fi
}

# Call the function to get the Day Ahead Prices data for tomorrow
get_day_ahead_prices
