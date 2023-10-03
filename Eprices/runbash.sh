#!/bin/bash
echo "Starting workflow"

echo "Getting new data"
./get_electricity_prices.sh
echo "implementing changes"
./get_csv.sh

