import random
import threading
import time
import datetime

import urllib3
import pytz
from timezonefinder import TimezoneFinder  # offline module to return timezone from 'lat' and 'lon'
import json
import requests

from haversine import haversine, Unit  # used to calculate distance between the latest used location and the location picked-up form gps

import serial  # ESP32 board communicates with the RPI board via serial. It sends GPS, LORA and sensors data over it
import bme680
import SDL_Pi_INA3221

import atexit  # allow running methods when a 'program exit' is registered.

from events import Signals as sig
from tools import timestamp_to_friendly_time, timestamp_to_description, overal_list_trend, wind_decode

"""
ABOUT THIS MODULE:
sense_skills.py contains all the sensing classes and methods that the PDA can do.
Every sense class has a thread loop, running in a background, so the PDA can update it independently.
If a new sense needs to be added, a class related to it should be witten here,
and then included in the class SenseSingleton.
Note: The Listening (and speech_to_text) skill is not located here, but in sense.py module.
"""


# =================== SINGLETON Design Pattern ====================
# the class implements Singleton Design pattern.
# This will ensure that only one instance of a classes 'Connection', 'Location', etc...
# will be created and only one thread of each sense will run.
# The instances then are accessed from all the place in the code
# including classes, functions and the main class as well, in every file.
# This is important, because, for example, the connection and the location information
# is required for many classes at the same time
class SenseSingleton:
    """Implements a singleton usage of every class responsible for sensing the environment."""
    __instance = None

    def __init__(self):
        print("Instancing Connection...")
        self.connection = Connection()
        time.sleep(2)
        print("Instancing Location...")
        self.location = Location()
        print("Instancing Environment...")
        self.environment = Environment()

        atexit.register(self.clear)

    @classmethod
    def get_instance(cls):
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    # @classmethod
    # def get_instance(cls):
    #     return cls.__instance
    #
    # @classmethod
    # def create_instance(cls):
    #     cls.__instance = cls()

    def clear(self):
        del self.connection
        del self.location
        # del self.environment


# ======================= class LOCATION ==========================
# The class have functions to constantly update the current location.
# The class uses GPS sensor and the HERE API to get the full information of the current coordinates.
class Location:
    # __coord_list = {
    #     "Bradford": [(53.7938, -1.7564), 'UK', 'BD1', 'Europe/London', 'BDQ'],
    #     "Keighley": [(53.8678, -1.9124), 'UK', 'BD20', 'Europe/London', 'KEI'],
    #     "Leeds": [(53.8008, -1.5491), 'UK', 'LS16', 'Europe/London', 'LDS'],
    #     "Manchester": [(53.4808, -2.2426), 'UK', 'M1', 'Europe/London', 'MCV'],
    #     "London Kings Kross": [(51.5347, 0.1246), 'UK', 'N1 9AL', 'Europe/London', 'KGX'],
    #     "London": [(51.5072, 0.1276), 'UK', 'N1 9AL', 'Europe/London', 'KGX'],
    #     "Gatwick Airport": [(51.1537, 0.1821), 'UK', 'RH6 0NP', 'Europe/London', 'GTW'],
    #     "Ruse": [(43.8356, 25.9657), 'BG', '7001', 'Europe/Sofia', ''],
    #     "Varna": [(43.2141, 27.9147), 'BG', '9000', 'Europe/Sofia', ''],
    #     "Burgas": [(42.5048, 27.4626), 'BG', '8000', 'Europe/Sofia', ''],
    #     "Plovdiv": [(42.1354, 24.7453), 'BG', '4000', 'Europe/Sofia', ''],
    #     "Chepelare": [(41.7248, 24.6856), 'BG', '4850', 'Europe/Sofia', ''],
    #     "Sofia": [(42.6977, 23.3219), 'BG', '1000', 'Europe/Sofia', ''],
    # }

    __coord_list = {
        "Bradford": {"city": "Bradford", "lat": "53.7938", "lon": "-1.7564", "alt": None, "tz": 'Europe/London', "code": 'UK', "country": 'England', "post": None, "str": None},
        "Keighley": {"city": "Keighley", "lat": "53.8678", "lon": "-1.9124", "alt": None, "tz": 'Europe/London', "code": 'UK', "country": 'England', "post": None, "str": None},
        "Leeds": {"city": "Leeds", "lat": "53.8008", "lon": "-1.5491", "alt": None, "tz": 'Europe/London', "code": 'UK', "country": 'England', "post": None, "str": None},
        "Manchester": {"city": "Manchester", "lat": "53.4808", "lon": "-2.2426", "alt": None, "tz": 'Europe/London', "code": 'UK', "country": 'England', "post": None, "str": None},
        "London": {"city": "London", "lat": "51.5072", "lon": "-0.1276", "alt": None, "tz": 'Europe/London', "code": 'UK', "country": 'England', "post": None, "str": None},
        "Gatwick Airport": {"city": "Gatwick Airport", "lat": "51.1537", "lon": "-0.1821", "alt": None, "tz": 'Europe/London', "code": 'UK', "country": 'England', "post": None, "str": None},

        "Ruse": {"city": "Ruse", "lat": "43.8356", "lon": "25.9657", "alt": 43, "tz": 'Europe/Sofia', "code": 'BG', "country": 'Bulgaria', "post": '7000', "str": None},
        "Varna": {"city": "Varna", "lat": "43.2141", "lon": "27.9147", "alt": None, "tz": 'Europe/Sofia', "code": 'BG', "country": 'Bulgaria', "post": '9000', "str": None},
        "Burgas": {"city": "Burgas", "lat": "42.5048", "lon": "27.4626", "alt": None, "tz": 'Europe/Sofia', "code": 'BG', "country": 'Bulgaria', "post": '8000', "str": None},
        "Plovdiv": {"city": "Plovdiv", "lat": "42.1354", "lon": "24.7453", "alt": None, "tz": 'Europe/Sofia', "code": 'BG', "country": 'Bulgaria', "post": '4000', "str": None},
        "Chepelare": {"city": "Chepelarey", "lat": "41.7248", "lon": "24.6856", "alt": 1050, "tz": 'Europe/Sofia', "code": 'BG', "country": 'Bulgaria', "post": '4850', "str": None},
        "Sofia": {"city": "Sofia", "lat": "42.6977", "lon": "23.3219", "alt": None, "tz": 'Europe/Sofia', "code": 'BG', "country": 'Bulgaria', "post": '1000', "str": None},

    }
    # TODO: using reverse geo location from HERE app to retrieve information about given town name.

    __HERE_API = '...'  # !!! put your HERE api access key here !!!

    def __init__(self, default_location_town=None):
        # self.is_online = SenseSingleton.get_instance().connection.is_internet
        # self.is_online = False

        self.latitude = None
        self.longitude = None
        self.altitude = None
        self.timezone = None
        self.country = None
        self.code = None
        self.city = None
        self.street = None
        self.post = None

        self.location_data = None  # Keeps all the location data as dictionary.

        self.is_error = ""

        try:
            self.__ser = serial.Serial(
                port="/dev/serial0",
                baudrate=115200,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
            )
        except Exception as e:
            print(e)
            self.__ser = None
            self.is_error += "Serial Init ERR | "

        self.__load_location_data(default_location_town)

        self.thread_is_finished = False
        self.thread = threading.Thread(target=self.update_gps_thread)
        self.thread.start()

    @staticmethod
    def is_online():
        return SenseSingleton.get_instance().connection.is_internet

    # the function is used to set a default location data parameters when we start the program.
    # It uses the @staticmethod below, to search and load location data from the locations.txt file.
    def __load_location_data(self, default_location_town):
        location_data = self.get_location_from_file(default_location_town)
        if location_data:
            try:
                self.latitude = float(location_data["lat"])
                self.longitude = float(location_data["lon"])
                self.altitude = float(location_data["alt"])

                try:
                    self.timezone = pytz.timezone(location_data["tz"])
                except Exception as e:
                    print(e)
                    self.is_error += 'ERR loading the timezone | '

                self.city = location_data["city"]
                self.country = location_data["country"]
                self.code = location_data["code"]
                self.street = location_data["str"]
                self.post = location_data["post"]

                # print(f"Location data loaded from locations.txt successfully. Town set to '{self.city}'")
            except Exception as e:
                print(e)
                self.is_error += "Location data File ERR | "
        else:
            self.is_error += "ERR: Location data not loaded | "

    @staticmethod
    def get_location_from_file(town_name):
        with open('db/locations.txt', 'r') as file:
            lines = file.readlines()

            if town_name:
                # Reverse the list of lines to search from the last to the first
                for line in reversed(lines):
                    data = json.loads(line)
                    if 'city' in data.keys() and data['city'] == town_name:
                        return data

            # If no match found, parse the last non-empty line as a JSON-encoded dictionary
            for line in reversed(lines):
                # print(line)
                line = line.strip()
                if line:
                    return json.loads(line)

        return None

    @staticmethod
    def save_location_to_file(location_data):
        if location_data:
            try:
                # Attempt to parse the location data as JSON
                location_json = json.dumps(location_data)
                # If the data is valid JSON, append it to the file
                filename = 'db/locations.txt'
                with open(filename, 'a') as file:
                    file.write(location_json + "\n")

            except json.JSONDecodeError:
                return False

            return True
        else:
            return False

    # This method requests detailed location data from the HERE API...
    def get_here_data(self, lat, lon, api_key):
        # get all map data from HERE API
        city = None
        timezone = None
        country = None
        code = None
        post = None
        street = None
        try:
            tf = TimezoneFinder()
            timezone = tf.timezone_at(lng=lon, lat=lat)
        except Exception as e:
            print(e)

        if self.is_online():
            try:
                # proccess the HERE request:
                url = f'https://revgeocode.search.hereapi.com/v1/revgeocode?at={lat}%2C{lon}&lang=en-US&apiKey={api_key}'
                

                response = requests.get(url)
                result = response.json()

                city = result["items"][0]["address"]["city"]
                country = result["items"][0]["address"]["countryName"]
                code = result["items"][0]["address"]["countryCode"]
                street = result["items"][0]["address"]["street"]
                post = result["items"][0]["address"]["postalCode"]


            except Exception as e:
                print(e)
                self.is_error += "ERR in HERE API | "

        return city, country, code, timezone, street, post

    def get_reversed_here_data(self, city_name):
        ...

    # Constantly updating the location, using onboard gps and the HERE API (for the address)
    def update_gps_thread(self):
        # print("GPS Thread started successfully.")

        # The data received from uart pins (gps) is in format:
        # b'{"dev":"GPS","lat":"53.87337","lon":"-1.92530","alt":"238.5"}\r\n'

        # if self.__ser.isOpen() > 0:
        # Location thread refreshes every time we receive a new gps data from uart
        while self.__ser.isOpen() > 0 and not sig.program_terminate:
            if self.__ser.inWaiting() > 0:
                try:
                    raw = self.__ser.readline().decode().strip()
                    json_data = json.loads(raw)
                    # print(json_data)
                    if 'dev' in json_data.keys() and json_data["dev"] == "GPS":

                        # 1. read the gps data:
                        lat = None
                        lon = None
                        alt = None
                        try:
                            lat = float(json_data["lat"])
                            lon = float(json_data["lon"])
                            try:
                                alt = float(json_data["alt"])
                            except ValueError:
                                # Handle exception for invalid "alt" value
                                pass
                        except ValueError:
                            # Handle exception for invalid "lat" or "lon" value
                            pass

                        # 2. check if the latest recorded gps data is within 1km away
                        # and if yes, update the current location...
                        if self.latitude and self.longitude and lat and lon:
                            # if we already have current location sets, we check the distance and update...
                            try:
                                # The 'Haverstine' algorighm measures distance between 2 geo-coordinates:
                                distance = haversine((self.latitude, self.longitude), (lat, lon), unit=Unit.KILOMETERS)
                                if distance > 1:
                                    # ONLY if the new location is 1 km away from the last loaded 'current' location,
                                    # we request the location data from HERE and save it into our database.
                                    # and the new location will be set to 'current'.
                                    self.latitude = lat
                                    self.longitude = lon
                                    self.altitude = alt

                                    self.city, self.country, self.code, self.timezone, self.street, self.post = self.get_here_data(lat, lon, self.__HERE_API)

                                    # save location data to a file:
                                    if alt:
                                        alt_str = f"{alt}"
                                    else:
                                        alt_str = None
                                    self.location_data = {
                                        "city": self.city,
                                        "lat": f"{lat}",
                                        "lon": f"{lon}",
                                        "alt": alt_str,
                                        "tz": self.timezone,
                                        "code": self.code,
                                        "country": self.country,
                                        "post": self.post,
                                        "str": self.street}
                                    if self.save_location_to_file(self.location_data):
                                        pass
                                        # print("New location data saved successfully into 'db/locations.txt'.")
                                    else:
                                        print("An ERR occured while saving to 'db/locations.txt'.")
                            except Exception as e:
                                print(e)
                        else:
                            # Empty or non valid location data. Just pass...
                            pass

                except Exception as e:
                    print(e)

        self.thread_is_finished = True

    # method to get HERE location data (lat, lon...) from given town name.
    # Used when we need to ask for weather in some unknown town and we need its coordinates.
    def search_location_data(self, city):
        if city == "chap a lara":
            city = "Chepelare"

        if city in self.__coord_list.keys():
            location_data = self.__coord_list[city]

            return location_data
        else:
            # TODO: try to search online and get the location data from HERE app...
            # location_data = self.get_reversed_geo_data(city)

            return None

    def __del__(self):
        # start_time = time.time()
        self.thread.join()
        if self.thread_is_finished:
            print("'Location' thread STOPPED successfully.")
        else:
            print("'Location' thread did not finish properly, but it was STOPPED.")


# This class keeps and updates the information about curent connection states.
# It takes care for internet, radio and MQTT network connectivity.
# Using a thread loop, it constantly checks the connectivity and updates the state.
class Connection:
    # Currently, 216.58.192.142 is one of the IP addresses for google.com and the quickest to respond.
    __URL_TO_CHECK = 'google.com'

    def __init__(self):
        self.is_internet = False
        self.is_radio = False
        self.is_mqtt = False

        self.thread_is_finished = False
        self.thread = threading.Thread(target=self.connection_thread)
        self.thread.start()

    def check_for_internet(self):
        try:
            http = urllib3.PoolManager(timeout=2)
            r = http.request('GET', self.__URL_TO_CHECK, preload_content=False)
            code = r.status
            r.release_conn()

            if code == 200:
                # print("Connection to Internet : True")
                return True
            else:
                # print("Connection to Internet : False")
                return False
        except Exception as e:
            print(f"Err, while checking for Internet: {e}")
            return False

    @staticmethod
    def check_for_radio():
        return False

    @staticmethod
    def check_for_mqtt():
        return False

    def connection_thread(self):
        # print("'Connection' Thread STARTED successfully.")
        while not sig.program_terminate:
            self.is_internet = self.check_for_internet()
            # time.sleep(1)
            # self.is_radio = self.check_for_radio()
            # time.sleep(1)
            # self.is_mqtt = self.check_for_mqtt()

            # checking connectivity every 30 seconds... Do not wait if a program_terminate signal is set
            for i in range(30):
                if not sig.program_terminate:
                    time.sleep(1)
                else:
                    break

        self.thread_is_finished = True  # assures the method finished its work, after 'stop_thread' flag raises True

    # when the instance of Connection class is deleted, this function is called to assure we stop the thread...
    def __del__(self):
        start_time = time.time()
        # waiting the thread to stop (the while loop inside the thread function should finish
        # if for some reason it won't exit, a timeout of 5 seconds will cause the thread to stop
        self.thread.join()
        if self.thread_is_finished:
            print("'Connection' thread STOPPED successfully.")
        else:
            print("'Connection' thread did not finish properly, but it was STOPPED.")


# ---------- Instancing the ONBOARD SENSORS -------------
class SystemSnz:
    __CHARGE_CHANNEL = 1
    __PI_CHANNEL = 2

    def __init__(self):
        self.__power_snz = SDL_Pi_INA3221.SDL_Pi_INA3221(addr=0x40)

        self.battery_voltage = None
        self.charging_current = None
        self.consumption_current = None
        self.is_charging = False

        # TODO: get the core temperature and load

    def read_sensor_data(self):
        try:
            self.battery_voltage = round(self.__power_snz.getBusVoltage_V(self.__CHARGE_CHANNEL), 2)
            self.charging_current = round(self.__power_snz.getCurrent_mA(self.__CHARGE_CHANNEL), 2)
            self.is_charging = True if self.charging_current > 100 else False
            # .......

            # TODO: Returning a dictionary, instead of flag, to be used in 'seve data'
            return True

        except Exception as e:
            print("Exception while try to read SystemSnz")
            print(e)
            return False


class EnvSnz:
    def __init__(self):
        self.__env_snz = self.__load_bme680()

        self.last_updated = None
        self.temperature = None
        self.humidity = None
        self.pressure = None
        self.gas_index = None

    @staticmethod
    def __load_bme680():
        snz = bme680.BME680(0x77)
        snz.set_humidity_oversample(bme680.OS_2X)
        snz.set_pressure_oversample(bme680.OS_4X)
        snz.set_temperature_oversample(bme680.OS_8X)
        snz.set_filter(bme680.FILTER_SIZE_3)
        snz.set_gas_status(bme680.ENABLE_GAS_MEAS)
        snz.set_gas_heater_temperature(320)
        snz.set_gas_heater_duration(150)
        snz.select_gas_heater_profile(0)
        return snz

    def read_sensor_data(self):

        if self.__env_snz.get_sensor_data():
            self.temperature = round(self.__env_snz.data.temperature, 1) - 2.0
            self.humidity = round(self.__env_snz.data.humidity)
            self.pressure = round(self.__env_snz.data.pressure)

            if self.__env_snz.data.heat_stable:
                self.gas_index = round(self.__env_snz.data.gas_resistance)

            self.last_updated = int(time.time())
            data = {"time": self.last_updated, "t": self.temperature, "h": self.humidity, "p": self.pressure, "gas": self.gas_index}
            # print(f"BME read successfully:")
            # print(data)

            return data
        else:
            print("Exception while try to read BME sensor_data")
            return False


class OnboardSensors:
    def __init__(self):
        self.environmental = EnvSnz()
        self.systems = SystemSnz()


class RoomSensors:
    ...


class OutSensors:
    ...


class Weather:
    __WDR_TOKEN = '...'  # put your openWeatherMap API key here !!!
    __WDR_DB = ['db/environment.txt', 'db/last_weather.txt']

    def __init__(self):

        # data from the last weather update
        self.lat = None
        self.lon = None
        self.timezone = None

        self.weather_raw = None
        self.air_raw = None

        self.weather_data = None

        self.last_updated = None  # timestamp
        self.temperature = None
        self.feels_like = None
        self.temperature_min = None
        self.temperature_max = None
        self.humidity = None
        self.pressure = None
        self.conditions_description = None
        self.wind_speed = None
        self.wind_degree = None
        self.wind_description = None

        self.air_quality_description = None

        self.events_description = None

    @property
    def is_internet(self):
        return SenseSingleton.get_instance().connection.is_internet

    # @property
    # def timezone(self):
    #     return SenseSingleton.get_instance().location.timezone

    @staticmethod
    def __get_weather_events(hourly_list, timezone, current, search_from=0, search_to=0, search_for=False):
        """Return the weather events based on the hourly bases (next 48 hours).
        Method search for specific event, or generate an events summary.
        But here I use it only to generate an events summary, when updating the weather (see get_weather_api).
        """
        if search_to == 0 or search_to > len(hourly_list) - 1:  # ako tyrseniq period nadvishava chasovata prognoza, se tarsi do kraq na chasovata prognoza
            search_to = len(hourly_list) - 1
        else:
            search_to = search_from + search_to  # search_to  --- e broi zapisi koito da se tarsqt. za da stane rendj, trqbwa da se sabere sas search_from

        event_descr = ""
        event_descr_1 = ""
        now_is0 = ""
        now_is = ""
        search_flag = False

        what_expected_to_stop = ""
        if current['main'] in ['Rain', 'Thunderstorm', 'Drizzle', 'Tornado', 'Snow']:
            if search_for:
                if current['main'] in search_for and search_from == 0:
                    search_flag = True
            now_is0 = f"There is {current['description']} outside already."
            what_expected_to_stop = current['main']
            # it will rain all day / it is expected to stop at ..... today / tomorrow
            stop_time = 0
            stop_time0 = 0
            i = 0
            will_change_flag = False
            for elem in hourly_list:
                if elem['weather'][0]['main'] in ['Rain', 'Thunderstorm', 'Drizzle', 'Tornado', 'Snow']:
                    if elem['weather'][0]['main'] != current['main']:
                        if not will_change_flag:
                            change_time = timestamp_to_friendly_time(elem['dt'], timezone)
                            change_day = ''
                            if change_time['weekday'] == 'today':
                                change_day = ''
                            elif change_time['weekday'] == 'tomorrow':
                                change_day = ' tomorrow'
                            else:
                                change_day = f"on {change_time['weekday']}"
                            now_is += f" It may change to {elem['weather'][0]['description']} around {change_time['hours']}{change_time['ampm']}{change_day}. "
                            what_expected_to_stop = elem['weather'][0]['main']
                            will_change_flag = True
                    i = 0
                    stop_time0 = 0
                else:
                    if i == 0: stop_time0 = elem['dt']
                    i += 1  # ako imame 3 poredni chasa spral dajd, spirame
                    if i >= 3:
                        # stop_time = elem['dt']
                        stop_time = stop_time0
                        break
            if stop_time == 0:
                if will_change_flag:
                    now_is += "and it won't stop in the next 48 hours."
                else:
                    now_is += "It won't stop in the next 48 hours."
            else:
                friendly_time = timestamp_to_friendly_time(stop_time, timezone)
                if friendly_time['weekday'] in "today tomorrow":
                    now_is += f"The {what_expected_to_stop} is expected to stop at {friendly_time['hours']}{friendly_time['ampm']} {friendly_time['weekday']}."
                else:
                    now_is += f"The {what_expected_to_stop} is expected to stop on {friendly_time['weekday']} arount {friendly_time['hours']}{friendly_time['ampm']}."

        else:  # ako ne vali v momenta,
            now_is = ""

        # check for speciffic search... / initializing:
        if search_for and not search_flag:
            event_descr_1 = "No."

            for index in range(search_from, search_to):
                l_main = hourly_list[index]['weather'][0]['main']
                l_descr = hourly_list[index]['weather'][0]['description'].lower()
                start_time_dic = timestamp_to_friendly_time(hourly_list[index]['dt'], timezone)
                if start_time_dic['weekday'] in "today tomorrow":  # samo smenq izkazvaneto, kato dobavq "ON wenesday"
                    when_start = f"{start_time_dic['hours']}{start_time_dic['ampm']} {start_time_dic['weekday']}"
                else:
                    when_start = f"{start_time_dic['hours']}{start_time_dic['ampm']} on {start_time_dic['weekday']}"
                if l_main == 'Rain' and l_main.lower() in search_for:
                    if l_descr == "light rain":
                        event_descr_1 = f"Yes. There is a chance of light rain at {when_start}, about {round(hourly_list[index]['rain']['1h'], 1)}mm for one hour."
                        break
                    elif l_descr == "shower rain":
                        event_descr_1 = f"Yes. Expected showers at {when_start}, about {round(hourly_list[index]['rain']['1h'], 1)}mm for one hour."
                        break
                    elif l_descr in ["moderate rain", "freezing rain", "light intensity" "shower rain"]:
                        event_descr_1 = f"Yes. There is a chance of rain at {when_start}, about {round(hourly_list[index]['rain']['1h'], 1)}mm for one hour."
                        break
                    elif l_descr in ["heavy intensity rain", "very heavy rain", "extreme rain", "heavy intensity rain"]:
                        event_descr_1 = f"Yes. Heavy rain is expected at {when_start}, about {round(hourly_list[index]['rain']['1h'], 1)}mm for one hour. Be aware!"
                        break
                    elif l_descr in ["heavy intensity shower rain", "ragged shower rain"]:
                        event_descr_1 = f"Yes. There is warning of heavy showers coming at {when_start}, about {round(hourly_list[index]['rain']['1h'], 1)}mm for one hour."
                        break
                    else:
                        event_descr_1 = f"Yes. There is a chance of rain at {when_start}, about {round(hourly_list[index]['rain']['1h'], 1)}mm for one hour."
                        break
                elif l_main == 'Thunderstorm' and l_main.lower() in search_for:
                    if l_descr == "thunderstorm":
                        event_descr_1 = f"There is a chance of thunderstorm at {when_start}."
                        break
                    elif l_descr in ["thunderstorm with heavy rain", "heavy thunderstorm",
                                     "thunderstorm with heavy drizzle"]:
                        event_descr_1 = f"Yes. Heavy thunderstorm expected at {when_start}. Be aware!"
                        break
                    elif l_descr == "ragged thunderstorm":
                        event_descr = f"There is a warning of ragged thunderstorm at {when_start}. Be careful!"
                        break
                    else:
                        event_descr_1 = f"There is a chance of thunderstorm at {when_start}."
                        break
                elif l_main == 'Drizzle' and l_main.lower() in search_for:
                    event_descr_1 = f"Yes. Drizzle expected at {when_start}."
                    break
                elif l_main == 'Tornado' and l_main.lower() in search_for:
                    event_descr_1 = f"There is a warning of tornado around {when_start}. Be careful!"
                    break
                elif l_main == 'Snow' and l_main.lower() in search_for:
                    if l_descr == "heavy shower snow" or l_descr == "heavy snow" or l_descr == "shower snow" or l_descr == "shower sleet":
                        event_descr_1 = f"Yes. A heavy snow is expected at {when_start}, about {round(hourly_list[index]['snow']['1h'], 1)}mm for one hour."
                        break
                    elif l_descr == "rain and snow" or l_descr == "light rain and snow":
                        event_descr_1 = f"There is a chance of rain and snow mixed, at {when_start}, about {round(hourly_list[index]['snow']['1h'] + hourly_list[index]['rain']['1h'], 1)}mm for one hour."
                        break
                    else:
                        event_descr_1 = f"Yes. A snow is expected at {when_start}, about {round(hourly_list[index]['snow']['1h'], 1)}mm for one hour."
                        break

        if event_descr_1 == "" or event_descr_1 == "No.":
            if search_from == 0:
                event_descr = "Nothing expected in the next few hours."
            else:
                event_descr = "Nothing is expected for this time."
            # if there is event found, nothing expected became the name of event.
            for index in range(search_from, len(hourly_list) - 1):
                l_main = hourly_list[index]['weather'][0]['main']
                l_descr = hourly_list[index]['weather'][0]['description'].lower()
                start_time_dic = timestamp_to_friendly_time(hourly_list[index]['dt'], timezone)
                if start_time_dic['weekday'] in "today tomorrow":
                    when_start = f"{start_time_dic['hours']}{start_time_dic['ampm']} {start_time_dic['weekday']}"
                else:
                    when_start = f"{start_time_dic['hours']}{start_time_dic['ampm']} on {start_time_dic['weekday']}"

                if l_main == 'Rain':
                    if l_descr == "light rain":
                        event_descr = f"There is a chance of light rain at {when_start}."
                        break
                    elif l_descr == "shower rain":
                        event_descr = f"Expected showers at {when_start}."
                        break
                    elif l_descr in ["moderate rain", "freezing rain", "light intensity" "shower rain"]:
                        event_descr = f"There is a chance of rain at {when_start}."
                        break
                    elif l_descr in ["heavy intensity rain", "very heavy rain", "extreme rain", "heavy intensity rain"]:
                        event_descr = f"Heavy rain is expected at {when_start}. Be aware!"
                        break
                    elif l_descr in ["heavy intensity shower rain", "ragged shower rain"]:
                        event_descr = f"Heavy showers expected at {when_start}"
                        break
                    else:
                        event_descr = f"There is a chance of rain at {when_start}"
                        break
                elif l_main == 'Thunderstorm':
                    if l_descr == "thunderstorm":
                        event_descr = f"There is a chance of thunderstorm at {when_start}."
                        break
                    elif l_descr in ["thunderstorm with heavy rain", "heavy thunderstorm",
                                     "thunderstorm with heavy drizzle"]:
                        event_descr = f"Heavy thunderstorm expected at {when_start}. Be aware!"
                        break
                    elif l_descr == "ragged thunderstorm":
                        event_descr = f"There is a warning of ragged thunderstorm at {when_start}. Be careful!"
                        break
                    else:
                        event_descr = f"There is a chance of thunderstorm at {when_start}."
                        break
                elif l_main == 'Drizzle':
                    event_descr = f"There is a chance of drizzle at {when_start}."
                    break
                elif l_main == 'Tornado':
                    event_descr = f"There is a warning of tornado around {when_start}. Be careful!"
                    break
                elif l_main == 'Snow':
                    if l_descr == "heavy shower snow" or l_descr == "heavy snow" or l_descr == "shower snow" or l_descr == "shower sleet":
                        event_descr = f"A heavy snow expected at {when_start}."
                        break
                    elif l_descr == "rain and snow" or l_descr == "light rain and snow":
                        event_descr = f"There is a chance of rain and snow mixed, at {when_start}."
                        break
                    else:
                        event_descr = f"A snow is expected at {when_start}."
                        break

        # print (f"-------->>Now: {now_is}; 1: {event_descr_1}; ed: {event_descr}")
        if not now_is and event_descr_1 == "No." and 'Nothing' not in event_descr:
            out_stamp = f"{event_descr_1} But {event_descr}"
        elif not now_is and not search_for:
            out_stamp = event_descr
        elif not now_is:
            out_stamp = f"{event_descr_1} {event_descr}"
        elif now_is and search_from == 0 and event_descr_1 == "No.":
            out_stamp = f"{event_descr_1} But {now_is0} {now_is}"
        elif now_is and search_from == 0 and not search_for:
            out_stamp = now_is
        elif now_is and search_from == 0 and search_for:
            out_stamp = f"{now_is0} {now_is}"
        elif now_is and search_from != 0 and search_for and event_descr_1 == "No." and 'Nothing' not in event_descr:
            out_stamp = f"{event_descr_1} But {event_descr}"
        elif now_is and search_from != 0 and search_for and event_descr_1 and event_descr_1 != "No.":
            out_stamp = event_descr_1
        elif now_is and search_from != 0 and search_for and event_descr_1 == "No." and 'Nothing' in event_descr:
            out_stamp = f"{event_descr_1} {event_descr}"
        else:
            out_stamp = ""

        return out_stamp

    # TODO: Method to search for weather data. Uses the daily list. Search for temp/humid/pressure, wind, sunset/sunrise, air quality
    def search_for_weather_data(self, search_for, day_to_search="today", latitude=None, longitude=None):
        ...

    def get_weather_api(self, latitude, longitude, searching=False, forecast=False):
        """Function to get the weather and air quality data at some coordinates, from openWeatherMap API
        The method is used for updating the 'outside' weather conditions,
        as well as for searching of weather for specific location.
        """
        # print(f"Obtaining Weather Data: lat={latitude}, lon={longitude}, is_internet={self.is_internet}...")

        weather_link = "https://api.openweathermap.org/data/2.5/onecall?lat=" + str(latitude) + "&lon=" + str(longitude) + "&appid=" + self.__WDR_TOKEN + "&units=metric&exclude=minutely"
        air_link = "http://api.openweathermap.org/data/2.5/air_pollution?lat=" + str(latitude) + "&lon=" + str(longitude) + "&appid=" + self.__WDR_TOKEN
        

        air_quality_decode = ["", "Air quality is very good.", "Air quality is fair.", "Air quality is not perfect.",
                              "Be aware of a poor air quality.",
                              "Air quality is Very bad. You should wear protective equipment."]
        # try:
        #     tf = TimezoneFinder()
        #     timezone_str = tf.timezone_at(lng=longitude, lat=latitude)
        #     print(f"get_weather_api timezone = {timezone_str}")
        #     timezone = pytz.timezone(timezone_str)
        # except Exception as e:
        #     print("ERR: Timezone did not obtain! ")
        #     print(e)
        #     timezone = None

        # NOTE: when calling 'get_weather_api()' method, make sure you check for internet access in advance.
        if self.is_internet:
            try:
                weather_raw = requests.get(weather_link).json()
                air_raw = requests.get(air_link).json()
                if weather_raw is not None and air_raw is not None:
                    if 'cod' in weather_raw or 'cod' in air_raw:
                        return False
                    else:
                        try:
                            last_updated = weather_raw["current"]["dt"]

                            timezone = pytz.timezone(weather_raw["timezone"])

                            temperature = round(weather_raw['current']['temp'], 1)
                            feels_like = round(weather_raw['current']['feels_like'], 1)
                            temperature_min = weather_raw['daily'][0]["temp"]["min"]
                            temperature_max = weather_raw['daily'][0]["temp"]["max"]
                            humidity = weather_raw['current']['humidity']
                            pressure = weather_raw['current']['pressure']
                            conditions_description = weather_raw['current']['weather'][0]['description']
                            wind_speed = weather_raw['current']['wind_speed']
                            wind_degree = weather_raw['current']['wind_deg']
                            # wind_description = self.__wind_decode(wind_speed, wind_degree)
                            wind_description = wind_decode(wind_speed, wind_degree)
                            air_quality_description = air_quality_decode[air_raw['list'][0]['main']['aqi']]
                            # print(air_quality_description)
                            events_description = self.__get_weather_events(weather_raw['hourly'], timezone, weather_raw['current']['weather'][0])
                            # print(events_description)
                            # generate a dictionary with all obtaining data
                            weather_data = {"time": last_updated,
                                            "t": [temperature, feels_like, temperature_min, temperature_max],
                                            "h": humidity,
                                            "p": pressure,
                                            "conditions": conditions_description,
                                            "wind": wind_description,
                                            "air": air_quality_description,
                                            "events": events_description
                                            }
                            # print(weather_data)
                            if not searching:
                                # update the weather data ONLY if we do not search for another location:
                                self.lat = latitude
                                self.lon = longitude
                                self.timezone = timezone

                                self.weather_raw = weather_raw
                                self.air_raw = air_raw

                                self.weather_data = weather_data

                                self.last_updated = last_updated
                                self.temperature = temperature
                                self.feels_like = feels_like
                                self.temperature_min = temperature_min
                                self.temperature_max = temperature_max
                                self.humidity = humidity
                                self.pressure = pressure
                                self.conditions_description = conditions_description
                                self.wind_speed = wind_speed
                                self.wind_degree = wind_degree
                                self.wind_description = wind_description

                                self.air_quality_description = air_quality_description

                                self.events_description = events_description

                            return weather_data, weather_raw

                        except KeyError as e:
                            print(e)

                        except Exception as e:
                            print(e)

                else:
                    print("No weatherdata and air quality data obtained.")

            except requests.exceptions.RequestException as err:
                print(err)

        return None


# ---------- Class ENVIRONMENT: ------------
# The class is combining all the weather and environmental functions.
class Environment:
    def __init__(self):

        self.last_sensors = OnboardSensors().environmental
        self.last_weather = Weather()

        self.last_environment_data = None

        self.thread_is_finished = False
        self.thread = threading.Thread(target=self.update_environment_thread)

        self.thread.start()


    # return the latitude and longitude values from the singleton class.
    # this prevents recursion on initializing, when we call:
    # 'self.lat = SenseSingleton.get_instance().location.latitude' in the __init__
    @property
    def lat(self):
        return SenseSingleton.get_instance().location.latitude

    @property
    def lon(self):
        return SenseSingleton.get_instance().location.longitude

    # MAIN FUNCTION TO COMBINE ALL ENVIRONMENTAL DATA:
    def update_environment_data(self):
        """Function to combine all the environmental data into a one dictionary,
        and append it in the 'environment.txt' database file.
        The function is used in the 'update_environment_thread' method, calling it every 10 minutes.
        """
        filename = "db/environment.txt"

        # 1. refresh inside and outside environmental data:
        room_data = self.last_sensors.read_sensor_data()
        # TODO: this function actually not need of using weather_raw. When
        return_data = self.last_weather.get_weather_api(self.lat, self.lon)

        if not room_data:
            print("ERR while obtaining Room Data")

        if return_data is not None:
            # unpack if valid weather_api return:
            weather_data, weather_raw = return_data
        else:
            weather_data = None
            print("ERR while obtaining Weather Data")

        # 2. Generating a json string, combining both
        if room_data and weather_data:
            print("Environment data obtained successfully.")
            try:
                self.last_environment_data = {
                    "time": int(time.time()),
                    "room": {
                        "t": room_data["t"],
                        "h": room_data["h"],
                        "p": room_data["p"],
                        "gas": room_data["gas"],
                    },
                    "weather": {
                        "t": weather_data["t"],
                        "h": weather_data["h"],
                        "p": weather_data["p"],
                        "conditions": weather_data["conditions"],
                        "wind": weather_data["wind"],
                        "air": weather_data["air"],
                        "events": weather_data["events"],
                    }
                }

                # 3. Append the new data into environment database.
                with open(filename, 'a') as file:
                    file.write(json.dumps(self.last_environment_data) + "\n")

            except KeyError as k:
                print(f"ERR, while processing the environment data: {k}")
            except json.JSONDecodeError:
                print("ERR: No Environment data saved. Invalid json string.")
        else:
            print("ERR while reading the Environment data.")

    def search_for_weather_data(self, lat, lon):
        weather_data, weather_raw = self.last_weather.get_weather_api(lat, lon, searching=True)

        return weather_data

    # The thread updates the Environment data for the current location every 5 minutes.
    def update_environment_thread(self):
        # print("'Environment' Thread STARTED successfully.")
        while not sig.program_terminate:
            self.update_environment_data()

            # we update weather every 5 min, so we wait 300 x 1sec,
            # but if a 'program_terminate' signal is set, the waiting is terminated.
            for i in range(120):
                if not sig.program_terminate:
                    time.sleep(1)
                else:
                    break

        self.thread_is_finished = True  # Flag, proving the method finished its work.

    def __del__(self):
        start_time = time.time()
        # Waiting the thread to stop (the while loop inside the thread function  finish
        self.thread.join()
        if self.thread_is_finished:
            print("'Environment' thread stopped successfully.")
        else:
            print("'Environment' thread did not finish properly, but it was stopped.")


