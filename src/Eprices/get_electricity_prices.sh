#!/bin/bash

# API URL and token
API_URL="https://web-api.tp.entsoe.eu"
TOKEN="5a4b409d-69f5-4b05-a932-168759fe7589"

# Data directory
DATA_DIR="./data"

get_day_ahead_prices() {
    local current_date=$(date +"%Y%m%d")
    local current_time=$(date +"%H%M%S")
    local output_file="$DATA_DIR/day_ahead_prices_${current_date}_${current_time}.xml"
    local api_endpoint="/api?securityToken=$TOKEN&documentType=A44&in_Domain=10YBE----------2&out_Domain=10YBE----------2&periodStart=${current_date}2300&periodEnd=${current_date}2300"
    # Make the API request using cURL and save the output to the file
    curl -s "$API_URL$api_endpoint" -o "$output_file"

    # Check if the request was successful (HTTP status code 200)
    if [ $? -eq 0 ]; then
        echo "Day Ahead Prices data for tomorrow fetched and saved to $output_file."
    else
        echo "Failed to fetch Day Ahead Prices data for tomorrow from the API."
    fi
}

# Call the function to get the Day Ahead Prices data for tomorrow
get_day_ahead_prices
