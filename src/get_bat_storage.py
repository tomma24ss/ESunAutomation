import os
import math
from datetime import datetime, timedelta
import growattServer

def log_bat_state(storage_capacity, login_error=False):
    directory = '/home/pi/Automation/ESunAutomation/logs'
    filename = os.path.join(directory, "bat_states.txt")
    now = datetime.now()
    formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")
    if login_error:
        message = f"{formatted_time} - Login Error\n"
    else:
        message = f"{formatted_time} - {storage_capacity}\n"

    # Clean up old records
    new_lines = []
    one_hour_ago = now - timedelta(hours=1)
    try:
        with open(filename, 'r') as file:
            for line in file:
                parts = line.strip().split(" - ")
                if len(parts) > 1:
                    timestamp_str = parts[0]
                    log_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                    if log_time > one_hour_ago:
                        new_lines.append(line)
    except FileNotFoundError:
        pass  # If the file does not exist, we'll create a new one

    new_lines.append(message)
    with open(filename, 'w') as file:  # Overwrite the file with cleaned records
        file.writelines(new_lines)
    if login_error:
        print(f"Login error logged at {formatted_time}")
    else:
        print(f"Battery state logged: {storage_capacity}% at {formatted_time}")

def read_bat_state():
    directory = '/home/pi/Automation/ESunAutomation/logs'
    filename = os.path.join(directory, "bat_states.txt")
    try:
        with open(filename, 'r') as file:
            last_line = file.readlines()[-1]
            parts = last_line.strip().split(" - ")
            if len(parts) > 1:
                timestamp_str = parts[0]
                storage_capacity_str = parts[1]
                if storage_capacity_str == "Login Error":
                    storage_capacity = None
                else:
                    storage_capacity = float(storage_capacity_str)
                last_log_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                return last_log_time, storage_capacity
    except FileNotFoundError:
        print("Battery state log file not found.")
        return None, None
    except Exception as e:
        print(f"An error occurred while reading the battery state: {str(e)}")
        return None, None

def get_bat_storage():
    # Initialize the API with custom User-Agent
    api = growattServer.GrowattApi(False, "MIC5555")

    # Login with your credentials
    username = "kvlaemynck"
    password = "123456"
    login_response = api.login(username, password)

    # Check if login was successful
    if login_response.get('success', False):
        user_id = login_response['user']['id']
        print("Override default User-Agent")
        print("User-Agent: %s\nLogged in User id: %s" % (api.agent_identifier, user_id))

        # Get plant list
        plant_list = api.plant_list(user_id)
        if plant_list['success']:
            plants = plant_list['data']
            if plants:
                for plant in plants:
                    plant_id = plant['plantId']
                    plant_name = plant['plantName']
                    storage_capacity = plant.get('storageCapacity', 'N/A')
                    if storage_capacity != 'N/A':
                        storage_capacity = storage_capacity.replace('%', '')
                        try:
                            storage_capacity = float(storage_capacity)
                        except ValueError:
                            storage_capacity = 'N/A'
                    else:
                        print("Bat charge status N/A - set Bat on to ensure continuation in case of error.")
                        return False  # Set actief to False and stop further checks
                    print(f"Plant ID: {plant_id}")
                    print(f"Plant Name: {plant_name}")
                    print(f"Storage Capacity: {storage_capacity}")
                    print("="*40)
                    return storage_capacity
            else:
                print("No plants found.")
                log_bat_state(None, login_error=True)
        else:
            print("Failed to get plant list:", plant_list.get('msg', 'Unknown error'))
            log_bat_state(None, login_error=True)
    else:
        print("Login failed:", login_response.get('msg', 'Unknown error'))
        log_bat_state(None, login_error=True)
        return False  # Ensure it stays on in case of error

if __name__ == "__main__":
    last_log_time, storage_capacity = read_bat_state()
    if last_log_time is None or (datetime.now() - last_log_time) >= timedelta(minutes=4):
        storage_capacity = get_bat_storage()
        if storage_capacity is not False:
            log_bat_state(storage_capacity)
    else:
        print(f"Battery state read from log: {storage_capacity}% at {last_log_time}")

