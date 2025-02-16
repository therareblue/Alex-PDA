import json
import requests

def create_location_data_line_in_file():
    location_data = {
        "city": "Keighley",
        "lat": "53.87277",
        "lon": "-1.89658",
        "alt": "212.3",
        "tz": 'Europe/London',
        "code": "GBR",
        "country": "United Kingdom",
        "post": "BD21 4",
        "str": "Bradford Road"}

    # Open the file in 'a' (append) mode
    with open('locations.txt', 'a') as file:
        # Write the JSON-encoded result to the file
        file.write(json.dumps(location_data) + '\n')

    file.close()
    print("File written successfully.")

def create_weather_raw_file():
    pass
