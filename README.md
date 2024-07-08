# ESunAutomation

Welcome to ESunAutomation, an innovative green automation solution tailored for controlling high wattage electrical devices like heat pumps and boilers. This program is designed to run on a Raspberry Pi and utilizes relay switch pins to manage devices based on dynamic conditions to optimize energy consumption and cost.

## Features

- **Device Control**: Manage high wattage devices such as heat pumps and boilers directly via relay switches.
- **Smart Pin Selection**: Automatically selects which pins to activate based on system logic and external conditions.
- **Solar Integration**: Reads solar grid input and output to optimize device operation times, reducing reliance on grid electricity.
- **Dynamic Pricing Integration**: Operates in response to hourly dynamic electricity prices to minimize energy costs.
- **Optimization Algorithm**: Uses a sophisticated algorithm to ensure the cheapest and most efficient operation of connected devices, ideal for applications like maintaining warm water availability.

## Installation

### Prerequisites

- Raspberry Pi (Model 3B or newer recommended)
- Relay modules compatible with the Raspberry Pi
- Access to solar grid input/output data
- Access to dynamic electricity pricing API

### Hardware Setup

1. **Connect the Relay Modules**: Attach your relay modules to the GPIO pins on your Raspberry Pi. Ensure that they are compatible and correctly configured for high wattage handling.
2. **Device Connection**: Connect your heat pump or boiler to the relay modules, ensuring all electrical standards and safety protocols are adhered to.

### Software Setup

```bash
# Clone the repository
git clone https://github.com/tomma24ss/ESunAutomation.git

# Navigate to the repository folder
cd ESunAutomation

# Install required libraries
sudo pip3 install -r requirements.txt

# Setup environment variables
# (You'll need to set these according to your solar/grid API and your hardware setup)
export SOLAR_API_KEY='your_api_key_here'
export GRID_API_KEY='your_grid_api_key_here'

# Run the program
python3 main.py
