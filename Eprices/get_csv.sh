#!/bin/bash

# Directory containing XML files
XML_DIR="./data"

# Find the most recent XML file in the directory
recent_xml_file=$(ls -t "$XML_DIR"/*.xml | head -1)

# Check if there are any XML files in the directory
if [ -z "$recent_xml_file" ]; then
  echo "No XML files found in $XML_DIR."
  exit 1
fi

# CSV output file
CSV_OUTPUT_FILE="pricesall.csv"

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

echo "CSV file generated: $CSV_OUTPUT_FILE"
