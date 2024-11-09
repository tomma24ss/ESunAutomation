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
    local output_file="$DATA_DIR/day_ahead_prices_${current_date}.xml"
    local api_endpoint="/api?securityToken=$TOKEN&documentType=A44&in_Domain=10YBE----------2&out_Domain=10YBE----------2&periodStart=${tomorrow_date}0000&periodEnd=${tomorrow_date}2300"
    # Make the API request using cURL and temporarily store output
    local response=$(curl -s -w "%{http_code}" -o temp.xml "$API_URL$api_endpoint")
    
    # Check if the HTTP status code is 200 (OK)
    if [ "${response}" -eq 200 ]; then
        # Check if the temporary file is not empty
        if [ -s temp.xml ]; then
            mv temp.xml "$output_file"
            echo "$TIMESTAMP - Day Ahead Prices data for tomorrow fetched and saved to $output_file." >> "$LOG_FILE"
        else
            echo "$TIMESTAMP - Error: No data received from the API." >> "$LOG_FILE"
            rm temp.xml  # Clean up empty temporary file
        fi
    else
        echo "$TIMESTAMP - Error: Failed to fetch Day Ahead Prices data for tomorrow from the API. HTTP status code: ${response}." >> "$LOG_FILE"
        rm temp.xml  # Clean up temporary file
    fi
}

# Call the function to get the Day Ahead Prices data for tomorrow
get_day_ahead_prices
