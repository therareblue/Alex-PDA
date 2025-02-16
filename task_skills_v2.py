"""Refactored version of skill classes.
If a new skill needs to be written, it is placed here."""

import time, datetime, random
from collections import deque

import pytz
from timezonefinder import TimezoneFinder

from events import Signals as sig
from events import EventReporter as reporter

from brain import ConversationMemory as memory
from tools import timestamp_to_friendly_time, timestamp_to_description, overal_list_trend, wind_decode

# Command / Question common structure:
# {'id': 'alex', 'adj': 'could you', 'ask': 'tell me the weather'}
# {'id': 'alex', 'adj': 'could you', 'ask': 'play some music'}
# {"id": "alexandra", "ask": "what's the forecast for tomorrow"}


class Messages:
    """
    Used to generate a messages to user, during the task processing.
    For example, some methods will return a prior message like 'Ok', 'Sure!', 'Of course!' before the process starts.
    """
    @staticmethod
    def generate_prior_msg(slots):

        if 'adj' in slots.keys():
            if "can you" in slots['adj']:
                chs = ["Of course!", "Absolutely!"]
                return random.choice(chs)
            elif "could you" in slots['adj']:
                chs = ["Of course!", "I'd be delighted to.", "Yes."]
                return random.choice(chs)

        if 'ask' in slots.keys():
            if "tell me" in slots['ask'] or "give me" in slots['ask'] or "can you" in slots['ask']:
                chs = ["OK.", "Of course!", "Yes Sir.", "Sure.", "Sir!"]
                return random.choice(chs)
            elif "have you got" in slots['ask'] or "do you know" in slots['ask']:
                chs = ["Yes.", "I do Sir."]
                return random.choice(chs)
            elif "can i have" in slots['ask'] or "may i have" in slots['ask']:
                chs = ["Always Sir!", "Of course!", "Sure.", "Absolutely!", "Certainly!"]
                return random.choice(chs)

        elif 'cmd' in slots.keys():
            chs = ["Sure.", "OK.", "Sir!", "Yes Sir."]
            return random.choice(chs)

        return None


class SystemQueries(Messages):
    """
    Used for processing system queries like 'shut down', 'get onboard sensors', etc.
    """
    INTENT = 'system'

    # This will help to process the request if insufficient data provided.
    # - for example, if only answer slots were given, but no 'cmd' or 'ask'... THEY WILL BE TAKEN from history
    # history remembers the last 5 requests...
    history = deque(maxlen=5)

    @classmethod
    def get_history_last(cls) -> dict:
        # return cls.history
        if len(cls.history) > 0:
            return cls.history[-1]
        else:
            return None

    @classmethod
    def append_to_history(cls, slots_data):
        timestamp = int(time.time())
        data_to_add = {
            'timestamp': timestamp,
            'slots': slots_data
        }
        cls.history.append(data_to_add)

    @classmethod
    def get_most_used_from_history(cls):
        # TODO:This method will get the most used slots needed for an operation to be executed
        ...

    def process(self, slots: dict, senses):
        """
        This function needs:
        - keys: 'ask' / 'cmd'
        - cmd: 'shutdown'
        - ask: 'battery, battery status, battery charge, charge, core temperature
        """
        # TODO: Save the slots to history:
        # self.append_to_history(slots)

        return_msg = None
        note = None
        answer_expected = None
        if 'cmd' in slots.keys():
            if 'shutdown' in slots["cmd"]:

                if 'ans' in slots.keys():
                    if slots['ans'] in ["no cancel it", "cancel it", "rejected", "i reject", "no i don't", "no"]:
                        return_msg = "Shutting down cancelled."
                    elif slots['ans'] in ["yes", "yes i do", "i confirm", "yes do it", "confirmed", "yes i confirm"]:
                        chs = ['OK.', 'All right!']
                        return_msg = f"{random.choice(chs)} Shutting down..."
                        self.__shutdown()

                else:
                    # return a question for confirmation:
                    chs = ["Are you sure?", "Please confirm."]
                    return_msg = f"Preparing to shutdown... {random.choice(chs)}"
                    note = "You requested a shutdown. I asked for confirmation."

                    answer_expected = {
                        'intent': self.INTENT,
                        'note': note
                    }

                    # Note: when ANSWER_EXPECTED, ringing will start after the return_msg is spoken (in respond()).

                # It is a valid request. Save it in the memory, along with its completion status...
                memory.add_request(self.INTENT, slots, status='complete', note=note)
                # Also save it in the TASK history, for eventually later use
                self.append_to_history(slots_data=slots)

                yield return_msg, answer_expected

            elif "reboot" in slots["cmd"] or "restart" in slots["cmd"]:
                ...

        elif 'ask' in slots.keys():
            if 'charge' in slots['ask']:
                # return a message with the battery charge
                ...

            elif 'battery' in slots['ask']:
                # return the battery health and status.
                ...

            elif 'core temperature' in slots['ask']:
                # return the core temperature
                ...

    @staticmethod
    def __shutdown():
        sig.program_terminate = True


class TimeQueries(Messages):
    """
    Used for giving the current time and date on different locations.
    """

    INTENT = 'time'
    status_list = ['answer-expected', 'completed', 'canceled', 'failed']

    # history remember the last 5 requests.
    history = deque(maxlen=5)

    @classmethod
    def get_history_last(cls) -> dict:
        # return cls.history
        if len(cls.history) > 0:
            return cls.history[-1]
        else:
            return None

    @classmethod
    def append_to_history(cls, data):
        cls.history.append(data)

    @classmethod
    def get_most_used_from_history(cls):
        # TODO:This method will get the most used slots needed for an operation to be executed
        ...

    def process(self, slots: dict, senses):
        print(f"intent = 'time' | slots = {slots}")

        respond_msg = ""  # message to be spoken
        status = None  # status, telling if success or failde
        note = None  # if failed or cancelled, here will be the reason.
        answer_expected = None

        # 1. Returning a prior (init) message to user, to identify that the function will be executed:
        prior_msg = self.generate_prior_msg(slots)
        yield prior_msg

        try:
            if 'ask' in slots.keys():
                if 'time' in slots['ask']:

                    time_now = datetime.datetime.now(senses.location.timezone)

                    hour = time_now.hour
                    minute = time_now.minute

                    if minute == 0:
                        time_phrase = f"{hour} o'clock"
                    elif minute == 30:
                        time_phrase = f"half past {hour}"
                    elif minute < 30:
                        time_phrase = f"{minute} minutes past {hour}"
                    else:
                        hour += 1
                        if hour > 12:
                            hour -= 12
                        time_phrase = f"{60 - minute} minutes to {hour}"

                    time_str_v2 = time_now.strftime("%-I:%M %p")

                    chs = [f"It's {time_phrase} Sir.", f"It's {time_phrase}", f"It's {time_str_v2} Sir.", f"It's {time_str_v2}", f"The time now is {time_phrase}"]
                    respond_msg = random.choice(chs)
                    status = 'completed'

                    # It is a valid request. Save it in the memory, along with its completion status...
                    memory.add_request(self.INTENT, slots, status=status, note=note)

                    # TODO: What's the time in California / Ruse / New York

                elif 'day' in slots['ask'] or 'date' in slots['ask']:
                    # datetime_now = datetime.now(senses.location.timezone)
                    days_of_week = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                    day_name_to_speak = 'today is'
                    dt_today = datetime.datetime.now(senses.location.timezone)

                    if 'when' in slots.keys():
                        if slots['when'].lower() in days_of_week:
                            current_day = dt_today.weekday()
                            target_day = days_of_week.index(slots['when'].lower())

                            days_ahead = (target_day - current_day) % 7
                            if days_ahead == 0:
                                days_ahead = 7

                            dt = dt_today + datetime.timedelta(days=days_ahead)
                            day_name_to_speak = ''

                        elif 'tomorrow' in slots['when'] or 'tomorrow' in slots.values():
                            # dt_today = datetime.datetime.now(senses.location.timezone)
                            dt = dt_today + datetime.timedelta(days=1)
                            day_name_to_speak = 'tomorrow is'
                        else:
                            dt = dt_today

                    else:
                        dt = dt_today

                    # TODO: What day is on Wednesday

                    if not dt:
                        dt = dt_today

                    weekday = dt.strftime("%A")
                    day = dt.day
                    month = dt.strftime("%B")

                    if day == 1:
                        day_phrase = "first"
                    elif day == 2:
                        day_phrase = "second"
                    elif day == 3:
                        day_phrase = "third"
                    elif day == 21:
                        day_phrase = "twenty-first"
                    elif day == 22:
                        day_phrase = "twenty-second"
                    elif day == 23:
                        day_phrase = "twenty-third"
                    elif day == 31:
                        day_phrase = "thirty-first"
                    else:
                        last_digit = day % 10
                        if last_digit == 1:
                            day_phrase = f"{day}st"
                        elif last_digit == 2:
                            day_phrase = f"{day}nd"
                        elif last_digit == 3:
                            day_phrase = f"{day}rd"
                        else:
                            day_phrase = f"{day}th"

                    if day_name_to_speak == '':
                        msg_list = [f"On {weekday} will be {day_phrase} of {month}.",
                                    f"It will be, {day_phrase} of {month} Sir.",
                                    f"{day_phrase} of {month}."]

                    else:
                        msg_list = [f"{day_name_to_speak} {weekday}, {day_phrase} of {month}.",
                                    f"It's {weekday}, {day_phrase} of {month} Sir.",
                                    f"{weekday}, {day_phrase} of {month}."]

                    respond_msg = random.choice(msg_list)
                    status = 'completed'

                    memory.add_request(self.INTENT, slots, status=status, note=note)

                # else:
                #     respond_msg = "I can't answer Sir."
                #     status = 'failed'
                #     note = 'because of incomplete request input'
        except Exception as e:
            print(e)
            respond_msg = "I can't respond to that Sir. There was unexpected exception."
            # status = 'failed'
            # note = 'because an unexpected error occur'

        # memory.add_request(self.INTENT, slots, status=status, note=note)

        yield respond_msg, answer_expected


class ScheduleQueries(Messages):
    INTENT = 'schedule'

    history = deque(maxlen=5)

    def process(self, slots: dict, senses):
        return_msg = None
        answer_expected = None

        status = None
        note = ""

        prior_msg = self.generate_prior_msg(slots)
        yield prior_msg

        # TODO: a 'wake me up at..' skill in time_query.
        ...

        yield return_msg, answer_expected



class WeatherQueries(Messages):

    INTENT = 'weather'

    # history remember the last 5 requests.
    history = deque(maxlen=5)

    @staticmethod
    def summary_from_condition_description(event_main, description, when_start, info=None, where_to=""):
        # TODO: implement this method for more naturally respond for bad weather search requests.

        event_descr = None

        if event_main == 'Rain':
            if description == "light rain":
                if info is not None:
                    event_descr += f"there is a chance of light rain {where_to} at {when_start}, about {info}mm per hour."
                else:
                    event_descr = f"there is a chance of light rain {where_to} at {when_start}."
            elif description == "shower rain":
                if info is not None:
                    event_descr += f"showers expected at {when_start} {where_to}, with intensity of about {info}mm per hour."
                else:
                    event_descr = f"a showers expected {where_to} at {when_start}."
            elif description in ["moderate rain", "freezing rain", "light intensity" "shower rain"]:
                if info is not None:
                    event_descr += f"there is a chance of rain {where_to} at {when_start}, about {info}mm per hour."
                else:
                    event_descr = f"there is a chance of rain {where_to} at {when_start}."
            elif description in ["heavy intensity rain", "very heavy rain", "extreme rain", "heavy intensity rain"]:
                if info is not None:
                    event_descr += f"a heavy rain is expected at {when_start} {where_to}, with intensity of {info}mm per hour. Be aware!"
                else:
                    event_descr = f"heavy rain is expected {where_to} at {when_start}. Be aware!"
            elif description in ["heavy intensity shower rain", "ragged shower rain"]:
                if info is not None:
                    event_descr = f"a heavy showers expected at {when_start} {where_to}, with intensity of {info}mm per hour."
                else:
                    event_descr = f"a heavy showers expected {where_to} at {when_start}"
            else:
                if info is not None:
                    event_descr = f"there is a chance of rain {where_to} at {when_start} about {info}mm for one hour."
                else:
                    event_descr = f"there is a chance of rain {where_to} at {when_start}"

        elif event_main == 'Thunderstorm':
            if description == "thunderstorm":
                event_descr = f"there is a chance of thunderstorm {where_to} at {when_start}."
            elif description in ["thunderstorm with heavy rain", "heavy thunderstorm",
                                 "thunderstorm with heavy drizzle"]:
                event_descr = f"a heavy thunderstorm expected at {when_start} {where_to}. Be aware!"
            elif description == "ragged thunderstorm":
                event_descr = f"there is a warning of ragged thunderstorm {where_to} at {when_start}. Be careful!"
            else:
                event_descr = f"there is a chance of thunderstorm {where_to} at {when_start}."
        elif event_main == 'Drizzle':
            event_descr = f"there is a chance of drizzle {where_to} at {when_start}."
        elif event_main == 'Tornado':
            event_descr = f"there is a warning of tornado {where_to} around {when_start}. Be careful!"
        elif event_main == 'Snow':
            if description == "heavy shower snow" or description == "heavy snow" or description == "shower snow" or description == "shower sleet":
                event_descr = f"a heavy snow expected {where_to} at {when_start}."
            elif description == "rain and snow" or description == "light rain and snow":
                event_descr = f"a mix of rain and snow expected {where_to} at {when_start}."
            else:
                event_descr = f"a snow is expected {where_to} at {when_start}."

        return event_descr

    @staticmethod
    def __extract_bad_weather_events(search_for, day_to_search, weather_raw, town_name_to_speak=None, timezone=None):
        """Method to extract bad weather summary from the OpenWeatherMap weather api respond data.
        - It first searches in the daily list.
        - If something found, it checks if the timestamp is in the timestamp of hourly list.
        - if found in the hourly list, it obtains the detailed info when the condition starts.

        - if already is the condition happening, it loops in the hourly list to check when will stop.
        """
        bad_weather_conditions = ['rain', 'thunderstorm', 'drizzle', 'tornado', 'snow']

        is_founded = False
        day_in_the_list = False
        answer = None

        # 1. Weather_raw already obtained.
        # The town_name_to_speak will remain None if is current location. If not, it will be the name of the town searched

        # --> Add a town name to the answer, if searched for another location
        if town_name_to_speak:
            where_to = f" in {town_name_to_speak}"
        else:
            where_to = ""

        # TODO: ---> Use the summary_from_condition_description() method to generate more user-friendly response

        daily_data = weather_raw["daily"]
        hourly_data = weather_raw["hourly"]

        another_bad_days_list = []
        another_bad_condition = {
            "day-name": None,
            "condition-main": None,
            "condition-descr": None,
            "condition-info": None  # if rain, it saves the mm/h data.
        }

        another_bad_today_tomorrow = {}

        for day_data in daily_data:

            # --> Collecting the information for the day (name, data, how to speak it)
            day_name_data = timestamp_to_description(day_data["dt"], timezone=timezone)
            if day_name_data:
                day_name = day_name_data["day"]
            else:
                day_name = "today"
            if day_name in ["today", "tomorrow"]:
                day_name_to_speak = day_name
            else:
                day_name_to_speak = f"on {day_name}"

            # --> collect the day's conditions
            day_condition_main = day_data["weather"][0]["main"].lower()
            day_condition_descr = day_data["weather"][0]["description"].lower()

            # print(f"day name = {day_name} | main condition = {day_condition_main} | description = {day_condition_descr}")

            # --> Collecting details if a bed weather condition:
            day_bad_probability = None
            if "pop" in day_data.keys():
                if day_data["pop"] > 0:
                    prob_percent = round(day_data["pop"] * 100)
                    day_bad_probability = f'with probability of {prob_percent} percent'
            if "rain" in day_data.keys():
                day_bed_weather_details = f", about {day_data['rain']:.1f} mm {day_bad_probability}"
            elif "snow" in day_data.keys():
                day_bed_weather_details = f", about {day_data['snow']:.1f} mm {day_bad_probability}"
            else:
                day_bed_weather_details = ""

            # --> Check:
            if day_name == day_to_search:
                day_in_the_list = True

                # we have founded the day we are looking for. Check for bed_weather

                if day_condition_main in bad_weather_conditions:
                    # there is bed-weather condition in the searching day
                    # check if is the searched one:
                    if day_condition_main == search_for:
                        # print("--> Searched condition for searched day found. Processing:")
                        is_founded = True

                    condition_main = day_condition_main
                    condition_descr = day_condition_descr
                    hour_bad_probability = ""
                    hour_bad_start = ""

                    if day_name in ['today', 'tomorrow']:
                        # Search in the hour_data, to see the condition start time:

                        for hour_data in hourly_data:
                            day_date = datetime.datetime.fromtimestamp(day_data["dt"], tz=timezone)
                            hour_date = datetime.datetime.fromtimestamp(hour_data["dt"], tz=timezone)
                            hour_main = hour_data["weather"][0]["main"].lower()

                            if day_date == hour_date and hour_main in bad_weather_conditions:
                                # The first occurance of the bad condition found. This is the time of start.
                                hour_descr = hour_data["weather"][0]["description"].lower()
                                bad_condition_start = timestamp_to_description(hour_data["dt"], timezone=timezone)

                                if "pop" in day_data.keys():
                                    if hour_data["pop"] > 0:
                                        prob_percent = round(hour_data["pop"] * 100)
                                        hour_bad_probability = f' with probability of {prob_percent} percent'

                                condition_main = hour_main
                                condition_descr = hour_descr
                                hour_bad_start = f' at {bad_condition_start["hour"]}'
                                break

                    if not answer:
                        # answer wasn't updated with this first part.
                        if is_founded:
                            answer = f'Yes, {condition_descr} expected{hour_bad_start}{where_to} {day_name_to_speak}{day_bed_weather_details}.'
                        else:
                            if search_for in ["rain", "drizzle", "thunderstorm"] and day_condition_main != "snow":
                                answer = f'Yes, the forecast calls for {condition_descr}{hour_bad_start} {day_name_to_speak}{hour_bad_probability}.'
                                # - Yes, the forecast calls for heavy thunderstorm at 5pm tomorrow with probability of 23 percent.
                                # - Yes, the forecast calls for light rain in wednesday with probability of 43 percent.
                            else:
                                start_at = ""
                                if hour_bad_start:
                                    start_at = f". expected{hour_bad_start}"

                                answer = f"There will be {condition_descr} instead of {condition_main} {day_name_to_speak}{start_at}{day_bed_weather_details}."

                else:
                    # the day we search for, has no bed condition
                    pass

            else:
                # day name is not the searched day.
                if day_condition_main in bad_weather_conditions:
                    # --> There is bed-weather condition on another day (not the searched one)...

                    # Check if there is detailed data for that day (if is in the hourly list)

                    condition_main = day_condition_main
                    condition_descr = day_condition_descr

                    if day_name in ['today', 'tomorrow']:
                        hour_bad_probability = ""
                        hour_bad_start = ""
                        # - Check if there is deteiled data for {day_name}...
                        day_date = datetime.datetime.fromtimestamp(day_data["dt"], tz=timezone).day

                        for hour_data in hourly_data:
                            hour_date = datetime.datetime.fromtimestamp(hour_data["dt"], tz=timezone).day
                            hour_main = hour_data["weather"][0]["main"].lower()
                            # print(f"hour_date = {hour_date} | day_date = {day_date} || hour_main = {hour_main} | day_main = {day_condition_main}| is_bad_weather={hour_main in bad_weather_conditions}")
                            if hour_date == day_date and hour_main in bad_weather_conditions:
                                hour_descr = hour_data["weather"][0]["description"].lower()
                                bad_condition_start = timestamp_to_description(hour_data["dt"], timezone=timezone)

                                if "pop" in day_data.keys():
                                    if hour_data["pop"] > 0:
                                        prob_percent = round(hour_data["pop"] * 100)
                                        hour_bad_probability = f' with probability of {prob_percent} percent'
                                # answer_additional = f'{hour_descr} expected {bad_condition_start["day"]} {bad_condition_start["hour"]}{hour_bad_probability}.'
                                condition_main = hour_main
                                condition_descr = hour_descr
                                hour_bad_start = f'{bad_condition_start["hour"]}'
                                break

                        another_bad_today_tomorrow = {
                            "day-name": day_name,
                            "condition-main": condition_main,
                            "condition-descr": condition_descr,
                            "condition-info": hour_bad_probability,
                            "when-start": hour_bad_start
                        }

                    else:
                        if day_data['dt'] == daily_data[-1]['dt']:
                            day_name = f"next {day_name}"

                        another_bad_condition = {
                            "day-name": day_name,
                            "condition-main": day_condition_main,
                            "condition-descr": day_condition_descr,
                            "condition-info": day_bed_weather_details  # if rain/snow, it saves the mm and probability data.
                        }
                        another_bad_days_list.append(another_bad_condition)

        if not answer:
            answer = "No"

        if another_bad_today_tomorrow:

            # - 'but {another_bad_today_tomorrow["condition-descr"]} is expected{another_bad_today_tomorrow["when-start"]} {another_bad_today_tomorrow["day-name"]}{another_bad_today_tomorrow["condition-info"]}.'
            # - but light rain is expected at 5pm tomorrow with probability of 34 percent.
            if answer == "No":
                # Nothing found for the searched day and condition but another is found
                # We give the full another_bad_today_tomorrow info:
                answer += f'. But {another_bad_today_tomorrow["day-name"]} there is a chance of {another_bad_today_tomorrow["condition-descr"]}{where_to} around {another_bad_today_tomorrow["when-start"]}{another_bad_today_tomorrow["condition-info"]}.'

            else:
                # There is bad weather found for the searched day. We give only the day name of the 'another_bad_today_tomorrow'
                # inserting the day name into the another_bad_days_list:

                # add the day in the begining of the another_bad_days_list (using slice notation)
                # another_bad_days_list = [another_bad_today_tomorrow] + another_bad_days_list
                # print(f"inserting to another_bad_days_list...")
                another_bad_days_list.insert(0, another_bad_today_tomorrow)

        if another_bad_days_list:
            # generate a dictionary only with 'condition' as keys and for value a list of days []
            rainy_condition_list = {}
            for elem in another_bad_days_list:
                elem_main = elem["condition-main"]
                elem_day_name = elem["day-name"]
                if elem_main not in rainy_condition_list.keys():
                    rainy_condition_list[elem_main] = [elem_day_name]
                else:
                    rainy_condition_list[elem_main].append(elem_day_name)

            # generate the rest bed conditions string:
            conditions = []
            for condition, days in rainy_condition_list.items():
                condition_string = f'{condition} on {", ".join(days[:-1])} and {days[-1]}' if len(
                    days) > 1 else f'{condition} on {days[0]}'
                conditions.append(condition_string)

            result = f'{", ".join(conditions[:-1])} and {conditions[-1]}' if len(conditions) > 1 else conditions[0]

            # - Rain is also expected on wednesday, thursday and friday.
            if answer == "No":
                # Answer is still empty, because we found a bad weather condition in another day that is not today/tomorrow.
                # -> ', but there may be rain on wednesday, thirsday and friday, and some snow on sunday.
                answer += f". But{where_to} there may be {result}."

            else:
                # There is some condition already added.
                # -> ' There is also rain expected at wednesday, thirsday and friday.
                answer += f" There is also probabilities for {result}."

        # --> After the loop there should be the following info collected:
        #   - is_founded = True/False -> Is the searched bed weather condition for the searched day found?
        #   - is another_bed_days_list: and len(another_bed_days_list) -> is more bed weather days found?

        # --> Final check and return of the message.
        if answer == "No":
            if day_in_the_list:
                answer += f". Nothing is expected{where_to} for {day_to_search} or for the next few days."
            else:
                answer = f"I have no information for {day_to_search} Sir."

        return answer

    @staticmethod
    def info_from_formated_weather_part(weather_part):
        """Method, helping the __daily_forecast().
        It receives a dictionary with some weather info, and checks if rain/clouds/clear appear.
        If bed-weather-conditions found, it records its time and the info.
        """
        main_conditions_list = ['Rain', 'Thunderstorm', 'Drizzle', 'Tornado', 'Snow']
        rain_found = None
        clouds_found = False
        clear_found = False
        for elem in weather_part:
            # Loop to check for rain
            if elem["main"] in main_conditions_list:
                rain_found = {
                    'start': elem["time-data"]["hour"],
                    'main': elem["main"],
                    'descr': elem["descr"]
                }
                break
            elif elem["main"] == 'Clouds':
                clouds_found = True
            elif elem["main"] == 'Clear':
                clear_found = True

        return rain_found, clouds_found, clear_found

    def __daily_forecast(self, day_data_block, hourly_data_block, town_name_to_speak, timezone=None):
        """Method to generate the forecast for one day.
        It directly receives the hourly and the daily data_block only for the searched day.
        """
        main_conditions_list = ['Rain', 'Thunderstorm', 'Drizzle', 'Tornado', 'Snow']
        answer = None

        try:
            # day_name_data = self.timestamp_to_description(day_data_block["dt"], timezone=timezone)
            day_name_data = timestamp_to_description(day_data_block["dt"], timezone=timezone)
            day_descr = day_name_data["day-descr"]
            if day_name_data["day"] not in ['today', 'tomorrow']:
                day_name_to_speak = f'on {day_name_data["day"]}'
            else:
                # day_chs = [f'{day_name_data["day"]} {day_descr}', f' {day_descr} {day_name_data["day"]}', f'{day_name_data["day"]}']
                # day_name_to_speak = random.choice(day_chs)
                day_name_to_speak = f'{day_name_data["day"]}'
                # note: randomly choose to add a date to the week-name, if not 'today'/'tomorrow'.

            # weather data block for the searched day is the main data for the forecast.
            if day_data_block["weather"][0]["main"] in main_conditions_list:
                answer = f'Forecast in {town_name_to_speak} calls for {day_data_block["weather"][0]["description"]} {day_name_to_speak} with temperatures ranging between {day_data_block["temp"]["min"]:.1f} and {day_data_block["temp"]["max"]:.1f} degrees.'
            else:
                description = day_data_block["weather"][0]["description"]
                if 'clouds' in description:
                    answer = f'According the forecast, {description} are mainly expected in {town_name_to_speak} {day_name_to_speak} with temperatures between {day_data_block["temp"]["min"]:.1f} and {day_data_block["temp"]["max"]:.1f} degrees.'
                elif 'clear' in description:
                    answer = f'A beautifull weather expected in {town_name_to_speak} {day_name_to_speak} with clear skies and temperatures up to {day_data_block["temp"]["max"]:.1f} degrees.'
                else:
                    answer = f'According the forecast, mainly a {description} is expected in {town_name_to_speak} {day_name_to_speak}. The temperature will range between {day_data_block["temp"]["min"]:.1f} and {day_data_block["temp"]["max"]:.1f} degrees.'

            if hourly_data_block:
                # It means we are looking for today/tomorrow and need to return more detailed forecast:
                """
                - We loop through the available hourly data (the input hourly data is only for the day we interested in)
                - We collect the needed info for every 3-4 hours of the part of the day.
                - In the end of the part of the day, we loop in the collected part and check for rain/clouds/clear.
                - Appended messages will be only for the part of the day we have available in the hourly_data_block.
                - If we miss the first part of the day (for example, asked the weather for today, but we are afternoon,
                    it will give hourly info only for the afternoon and the evening.

                """
                day_part = []  # during the loop, it feels with 'morn', 'mid', 'eve', 'end', coresponding of the part of the day.
                morn = None
                mid = None
                end = None

                for hourly_weather in hourly_data_block:

                    # time_data = self.timestamp_to_description(hourly_data_block[0]["dt"], timezone=timezone)
                    time_data = timestamp_to_description(hourly_weather["dt"], timezone=timezone)
                    hour = datetime.datetime.fromtimestamp(
                        hourly_weather["dt"]).hour  # get the hour in format 0-23, int.
                    hour_data_needed = {'time-data': time_data, 'hour': hour,
                                        'main': hourly_weather["weather"][0]["main"],
                                        'descr': hourly_weather["weather"][0]["description"]}

                    # we loop through the list and generate message according what is happening in the day
                    # print(f"hour={hour}")

                    if 6 <= hour < 11 and not morn:
                        # print(f"6 <= hour({hour}) < 11...")
                        # print(f"--> appending to day_part: {hour_data_needed}")
                        day_part.append(hour_data_needed)
                        if hour == 10:
                            # the below line is moved in a @staticmethod, to be used several times.
                            rain_found, clouds_found, clear_found = self.info_from_formated_weather_part(day_part)

                            if rain_found is not None:
                                answer += f' The day begins with {rain_found["descr"]} started at {rain_found["start"]}.'
                                morn = rain_found["main"]
                            else:
                                if clear_found:
                                    if clouds_found:
                                        answer += f' The morning will be mostly clear with just a few clouds.'
                                        morn = 'clouds'
                                    else:
                                        answer += f' The day will start with clear skies and sunshine.'
                                        morn = 'clear'
                                else:
                                    answer += f' The morning will be cloudy.'
                                    morn = 'clouds'

                            day_part = []

                    elif 11 <= hour < 18 and not mid:
                        # print(f"11 <= hour({hour}) < 18...")
                        # print(f"--> appending to day_part: {hour_data_needed}")
                        day_part.append(hour_data_needed)
                        if hour == 17:
                            rain_found, clouds_found, clear_found = self.info_from_formated_weather_part(day_part)

                            if rain_found is not None:
                                if morn in main_conditions_list:
                                    if morn == rain_found["main"]:
                                        answer += f' The {rain_found["main"].lower()} will continue during the day'
                                    else:
                                        answer += f' Bed weather continues with {rain_found["descr"]}'
                                else:
                                    answer += f' A {rain_found["descr"]} is expected later started at {rain_found["start"]}.'
                                mid = rain_found["main"]
                            else:

                                if clear_found:
                                    if clouds_found:
                                        if morn in main_conditions_list:
                                            answer += f' The {morn.lower()} will give away later in the day.'
                                        else:
                                            answer += f' Few clouds are expected during the day but there will be mostly sunny.'
                                        mid = 'clouds'
                                    else:
                                        if morn in main_conditions_list:
                                            answer += f' The {morn.lower()} will give away to sun during the day, providing perfect chance for outdoor activities.'
                                        mid = 'clear'
                                else:
                                    if morn in main_conditions_list:
                                        answer += f' The {morn.lower()} will give away during the day but the clouds will let no shine.'
                                    mid = 'clouds'

                            day_part = []

                    elif hour > 17 and not end:
                        # print(f"hour({hour}) > 17...")
                        # print(f"--> appending to day_part: {hour_data_needed}")
                        day_part.append(hour_data_needed)
                        if hour > 10:
                            rain_found, clouds_found, clear_found = self.info_from_formated_weather_part(day_part)

                            if rain_found is not None:
                                if mid in main_conditions_list:
                                    if not clouds_found and clear_found:
                                        answer += ' and is not expected to stop.'
                                    else:
                                        answer += 'and it may stop in the evening.'
                                else:
                                    answer += f' In the evening there is {rain_found["descr"]} expected around {rain_found["start"]}.'

                                end = rain_found["main"]
                            else:
                                if mid in main_conditions_list:
                                    answer += ' and it may stop in the evening.'
                                    end = 'clouds'
                                else:
                                    if clear_found:
                                        if clouds_found:
                                            answer += f' Mostly clear evening with no rain expected.'
                                            end = 'clouds'
                                        else:
                                            chs = ['providing the perfect opportunity for stargazers.', 'with no rain.']
                                            answer += f' The evening will be clear {random.choice(chs)}'
                                            end = 'clear'
                                    else:
                                        answer += ' The evening will be cloudy but no rain is expected.'
                                        end = 'clouds'
                            day_part = []
                            break

                # print("Loop complete.")
                # print(f"after the loop answer = {answer}")

            wind_speed = day_data_block["wind_speed"]
            wind_gusts = day_data_block["wind_gust"]
            wind_degree = day_data_block["wind_deg"]
            # print(f"wind_speed={wind_speed} | wind_gusts={wind_gusts} | wind_degree={wind_degree}")

            if wind_speed <= 6:
                # wind_decoded_info = self.__wind_decode(wind_speed, wind_degree)
                wind_decoded_info = wind_decode(wind_speed, wind_degree)
                if wind_gusts < 4:
                    chs = [" There is not much wind expected, so you can enjoy your favorite hats.",
                           " No wind for sailors on this day but will be great for picnic.",
                           f" There won't be much wind {day_name_to_speak}."]
                else:
                    chs = [f" There will be some {wind_decoded_info} but not so bad.",
                           f" Expected {wind_decoded_info}.",
                           " There may be some stronger wind gusts, but the overall wind may not be enough for sailing.",
                           f" Not much wind expected {day_name_to_speak}, but there may be some stronger wind gusts."]
            else:
                # wind_decoded_info = self.__wind_decode(wind_speed, wind_degree, return_short=True)
                wind_decoded_info = wind_decode(wind_speed, wind_degree, return_short=True)
                if wind_gusts > 10:
                    chs = [f" {wind_decoded_info} expected {day_name_to_speak} so keep your coat handy.",
                           f" Expected {wind_decoded_info} and some stronger gusts.",
                           f" {wind_decoded_info} is expected {day_name_to_speak}. There may be some stronger gusts, perfect for sailors."]
                else:
                    chs = [f"  {wind_decoded_info} expected {day_name_to_speak} so keep your coat handy.",
                           f" Expected {wind_decoded_info} {day_name_to_speak}.",
                           f" There is {wind_decoded_info} {day_name_to_speak}, and the temperature may feel colder."]
            wind_string = random.choice(chs)

            answer += wind_string

            sunrise_dt = datetime.datetime.fromtimestamp(day_data_block["sunrise"], tz=timezone)
            sunset_dt = datetime.datetime.fromtimestamp(day_data_block["sunset"], tz=timezone)

            sunrise_str = f"{sunrise_dt.strftime('%-I:%-M %p')}"
            sunset_str = f"{sunset_dt.strftime('%-I:%-M %p')}"
            daylight_time = (day_data_block["sunset"] - day_data_block["sunrise"]) // 3600
            chs = [f" giving about {daylight_time} hours of daylight.", ".",
                   f" with about {daylight_time} hours of daylight"]

            if day_name_data["day"] == 'today':
                if hourly_data_block is not None:
                    now_is = hourly_data_block[0]["dt"]
                    if day_data_block["sunrise"] < now_is < day_data_block["sunset"]:
                        answer += f' The sun came up at {sunrise_str} and will set at {sunset_str}{random.choice(chs)}'
                    elif now_is > day_data_block["sunset"]:
                        answer += f' The sun was set already. However there was about {daylight_time} hours of daylight today.'
                    else:
                        answer += f' Sun will rise at {sunrise_str} and set at {sunset_str}{random.choice(chs)}'
                else:
                    answer += f' Sun will rise at {sunrise_str} and sets at {sunset_str}{random.choice(chs)}'
            else:
                answer += f' The sunrise wil be at {sunrise_str} and will set at {sunset_str}{random.choice(chs)}'

        except Exception as err:
            print(err)

        return answer

    @staticmethod
    def __weekly_forecast(town_name, current_conditions, daily_data_list, hourly_data_list, timezone=None,
                          another_location=False):
        """Method to generate a forecast based on today and 7 days ahead.
        Used in the main method 'get_forecast()'
        Note: 'another_location' is a flag used to determine if we generate forecast for location different from current location.
        """

        main_conditions_list = ['Rain', 'Thunderstorm', 'Drizzle', 'Tornado', 'Snow']

        current_main = current_conditions['main']
        current_description = current_conditions['description']

        # 1. Obtain da data needed:
        todays_conditions = daily_data_list[0]
        tomorrows_conditions = daily_data_list[1]

        # Note: rest_conditions we get without the last day of the period, which is 'next today_name'
        rest_conditions = [daily_data_list[i] for i in range(2, len(daily_data_list) - 1)]
        third_day_name = datetime.datetime.fromtimestamp(daily_data_list[2]['dt'], tz=timezone).strftime("%A")

        # print(f"todays_conditions = {todays_conditions}")
        # print(f"tomorrows_conditions = {tomorrows_conditions}")
        # print(f"third_day_name = {third_day_name}")
        # print(f"today: {todays_conditions['weather'][0]['main']} | tomorrow: {tomorrows_conditions['weather'][0]['main']}")

        rainy_rest_of_week_text = ""

        # 2. generate the first part:
        is_rain_today_tomorrow = False
        if todays_conditions["weather"][0]["main"] == tomorrows_conditions["weather"][0]["main"]:

            if todays_conditions["weather"][0]["main"] in main_conditions_list:
                add_word = 'calls for'
                is_rain_today_tomorrow = True
            else:
                add_word = 'states for'

            if todays_conditions["weather"][0]["description"] == tomorrows_conditions["weather"][0]["description"]:
                answer = f"Forecast in {town_name} {add_word} {todays_conditions['weather'][0]['main']} today and tomorrow"
            else:
                answer = f"Forecast in {town_name} {add_word} {todays_conditions['weather'][0]['description']} today and {tomorrows_conditions['weather'][0]['description']} for tomorrow"
        else:
            if todays_conditions["weather"][0]["main"] in main_conditions_list or tomorrows_conditions["weather"][0]["main"] in main_conditions_list:
                is_rain_today_tomorrow = True

            answer = f"According the forecast, there is {todays_conditions['weather'][0]['description']} expected in {town_name} today and {tomorrows_conditions['weather'][0]['description']} for tomorrow"

        # print(answer)

        # print(f"is_rain_today_tomorrow={is_rain_today_tomorrow}")

        # 3. Provide detailed info if expected rain today/tomorrow
        if is_rain_today_tomorrow:
            if current_main in main_conditions_list:
                if another_location:
                    answer += f". It's currently {current_description.lower()} there."
                else:
                    answer += f". Currently is {current_description.lower()} outside, so make sure you have your umbrella."
            else:
                start_time_string = "."
                for hour_data in hourly_data_list:
                    main_condition = hour_data["weather"][0]["main"]
                    if main_condition in main_conditions_list:
                        # start_hour = self.timestamp_to_description(hour_data["dt"], timezone=timezone)
                        start_hour = timestamp_to_description(hour_data["dt"], timezone=timezone)
                        start_time_string = f" starting around {start_hour['hour']} {start_hour['day']}."
                        break
                if start_time_string:
                    answer += start_time_string
        else:
            answer += "."
        # print(answer)

        # 4. Collect the expected rainy conditions by days and add a rest of day conditions string:
        rainy_condition_list = {}
        for day in rest_conditions:
            if day["weather"][0]["main"] in main_conditions_list:
                day_main = day["weather"][0]["main"]
                day_weekname = datetime.datetime.fromtimestamp(day["dt"], tz=timezone).strftime("%A")

                if day_main in rainy_condition_list.keys():
                    rainy_condition_list[day_main].append(day_weekname)
                else:
                    rainy_condition_list[day_main] = [day_weekname]

            # print(f'{datetime.datetime.fromtimestamp(day["dt"], tz=timezone).strftime("%A")} --> {day["weather"][0]["main"]}')

        # print(f"rain_condition_list = {rainy_condition_list}")

        # Generate rest of the week conditions
        if todays_conditions["weather"][0]["main"] in main_conditions_list or tomorrows_conditions["weather"][0][
            "main"] in main_conditions_list:

            # get the condition type to compare:
            bed_condition_type = todays_conditions["weather"][0]["main"] if todays_conditions["weather"][0][
                                                                                "main"] in main_conditions_list else \
            tomorrows_conditions["weather"][0]["main"]

            if rainy_condition_list:
                conditions = []
                for condition, days in rainy_condition_list.items():
                    condition_string = f'{condition} on {", ".join(days[:-1])} and {days[-1]}' if len(
                        days) > 1 else f'{condition} on {days[0]}'
                    conditions.append(condition_string)

                result = f'{", ".join(conditions[:-1])} and {conditions[-1]}' if len(conditions) > 1 else conditions[0]

                answer += f" The bad weather continues with {result}."

            else:
                clear_sky_days = []
                for day in rest_conditions:
                    if day["weather"][0]["main"] == "clear sky":
                        day_weekname = datetime.datetime.fromtimestamp(day['dt'], tz=timezone).strftime("%A")
                        clear_sky_days.append(day_weekname)

                if clear_sky_days:
                    if third_day_name not in clear_sky_days:
                        answer += f" {bed_condition_type} will give away on {third_day_name}, and on {clear_sky_days[0]} the sun will shine again."
                    else:
                        answer += f" {bed_condition_type} will give away on {third_day_name} and the sun will shine again promising a chance for outdoor activities."
                else:
                    answer += f" {bed_condition_type} will give away on {third_day_name} but clouds will let no shine few days after."

        else:
            # rain is expected on Wenesday and Thirsday, and drizzle on saturday
            if rainy_condition_list:
                conditions = []
                for condition, days in rainy_condition_list.items():
                    condition_string = f'{condition} on {", ".join(days[:-1])} and {days[-1]}' if len(
                        days) > 1 else f'{condition} on {days[0]}'
                    conditions.append(condition_string)

                if len(conditions) > 1:
                    result = f'{", ".join(conditions[:-1])} and {conditions[-1]}'
                    answer += f" Weather turns bad then, with {result}."
                else:
                    answer += f" Expected {conditions[0]}."

        # print(f"answer after Generate rest of the week conditions:")
        # print(answer)

        # 5.  temperature information:
        # - Collencting the day temperature data in a list:
        temperature_list = []

        coldest_day = ('Monday', 50)  # initializing the lowest possible value
        warmest_day = ('Monday', -50)  # initializing the highest possible value
        coldest_morning = ('Monday', 50)  # a tuple = ('Monday', 8.4)
        for i in range(1, len(daily_data_list)):
            day_data = daily_data_list[i]
            day_name = "tomorrow" if i == 1 else datetime.datetime.fromtimestamp(day_data['dt'], tz=timezone).strftime(
                "%A")

            temperature_list.append(day_data["temp"]["day"])

            # get the mins and maxes:
            if day_data["temp"]["morn"] < coldest_morning[1]:
                coldest_morning = (day_name, day_data["temp"]["morn"])

            if day_data["temp"]["day"] < coldest_day[1]:
                coldest_day = (day_name, day_data["temp"]["day"])
            elif day_data["temp"]["day"] > warmest_day[1]:
                warmest_day = (day_name, day_data["temp"]["day"])

        # print(f"temperature list = {temperature_list}")

        # 6. Calculate the overall trend (increasing/decreasing) and the strength.
        temperature_trend_value = overal_list_trend(temperature_list)

        add_word = ""
        if abs(temperature_trend_value) > 15:
            add_word = "significantly"

        elif abs(temperature_trend_value) < 5:
            add_word = "slightly"

        if temperature_trend_value > 0:
            # if temperature_trend_value < 10: slightly increase.
            temperature_sentence = f" Temperature will increase {add_word} in the next few days"
            temperature_sentence += f" ranging between {round(coldest_day[1])} degrees on {coldest_day[0]} and {round(warmest_day[1])} degrees on {warmest_day[0]}."

        elif temperature_trend_value < 0:
            chs = ['drop', 'fall']
            if abs(temperature_trend_value < 5):
                temperature_sentence = f" The daily temperature slightly fall in the next few days"
            else:
                temperature_sentence = f" The daily temperature expected to {random.choice(chs)} {add_word} in the next few days"
            temperature_sentence += f" ranging between {round(warmest_day[1])} degrees on {warmest_day[0]} and {round(coldest_day[1])} degrees on {coldest_day[0]}."
        else:
            temperature_sentence = f" Overall daily temperature will remain the same in the next few days, about {coldest_day[1]:.1f} degrees."

        temperature_sentence += f" {coldest_morning[0]} morning will be the coldest with {coldest_morning[1]:.1f}"

        # print(f"temperature_sentence = {temperature_sentence}")

        answer += temperature_sentence

        # print(f"answer after temperature sentence:")
        # print(answer)

        # 7. Get the wind string:
        # wind_spead_list = []
        strongest_wind = {'speed': 0, 'deg': 0, 'day-name': 'monday'}
        for i in range(len(daily_data_list)):
            day_data = daily_data_list[i]
            wind_speed = day_data["wind_speed"]
            wind_deg = day_data["wind_deg"]

            if i == 0:
                day_name = "today"
            elif i == 1:
                day_name = "tomorrow"
            else:
                if i == len(daily_data_list) - 1:
                    day_name = f'next {datetime.datetime.fromtimestamp(day_data["dt"]).strftime("%A")}'
                else:
                    day_name = f'on {datetime.datetime.fromtimestamp(day_data["dt"]).strftime("%A")}'

            # wind_speed_elem = {'speed': wind_speed, 'deg': wind_deg, 'day-name': day_name}
            # wind_spead_list.append(wind_speed_elem)
            if wind_speed > strongest_wind['speed']:
                strongest_wind = {'speed': wind_speed, 'deg': wind_deg, 'day-name': day_name}

        # sorted_list = sorted(wind_spead_list, key=lambda x: x['speed'])
        # print(f"strongest_wind = {strongest_wind}")

        if strongest_wind['speed'] <= 8:
            wind_string = ". There will be not much wind these days so you can enjoy your favorite hats."
        else:
            # wind_decoded_info = self.__wind_decode(strongest_wind['speed'], strongest_wind['deg'], return_short=True)
            wind_decoded_info = wind_decode(strongest_wind['speed'], strongest_wind['deg'], return_short=True)
            # print(f"wind_decoded_info = {wind_decoded_info}")

            wind_string = f". {wind_decoded_info} expected {strongest_wind['day-name']} so keep your coat handy."

        # print(f"wind_string = {wind_string}")

        answer += wind_string

        # print(answer)
        """
        Forecast for Keighley states for clear sky today and tomorrow. Forecast in Keighhley states for light rain today and showers for tomorrow, starting at 3 PM..  / According the forecast, there will be clear sky totay and light rain for tomorrow.
        Clouds on wenesday will cover the sky and let no shine.

        Expected rain on Wenesday and Thursday, and 'drizzle' on friday.
        Temperature will raise/fall in the next few days, where tomorrow will be 13.5, going to 16.4 degrees on wenesday. 
        Friday morning will be the coldest, with 8.3. 
        Moderate winds from west expected on Thirsday, so keep your coat by hand.
        There will be not much wind these days, so you can enjoy your favorite hats.
        And be prepared for sleepless Wenesday while the full moon will rule the night sky.

        -- Forecast for {Keighley} states for {light rain} {today and tomorrow/today and cloudy tomorrow}. Clouds expected on Wenesday too but will be no rain.  
        Cloudns will give away on {Wenesday}, promising a chance for outdoor activities.
        Temperature will range between 5 degrees (on monday morning) and 25 degrees (on wenesday afternoon).
        If you plan to go out today, {be aware of light rain / you are lucky with the clear sky}
        Just don't forget to take your coat because the wind may not be joyful, especially on {wednesday}.

        """
        return answer

    # Function to search a forecast data
    def get_forecast(self, weather_data, weather_raw, town_name, day_to_search=None, search_for_next=False, search_for_another_location=False):
        # print(f"--> Running: 'get_forecast(town_name={town_name}, day_to_search={day_to_search}, search_for_next={search_for_next}, latitude={latitude}, longitude={longitude})")

        main_conditions_list = ['Rain', 'Thunderstorm', 'Drizzle', 'Tornado', 'Snow']

        search_data = None

        answer = None

        if weather_data and weather_raw:

            try:
                timezone = pytz.timezone(weather_raw["timezone"])

                current_conditions = weather_raw['current']['weather'][0]
                current_main = current_conditions['main']
                current_description = current_conditions['description']
                detailed_bed_weather = weather_data["events"]

                daily_data_list = weather_raw['daily']
                hourly_data_list = weather_raw["hourly"]  # used in weekly_forecast, for detailed info of bed_weather

                if day_to_search is not None:
                    day_data_block = None
                    hourly_block = []

                    for day_data in daily_data_list:
                        # day_name = self.timestamp_to_description(day_data["dt"], timezone=timezone)["day"]
                        day_name = timestamp_to_description(day_data["dt"], timezone=timezone)["day"]
                        # print(f"day_name={day_name} | day_from_list= {timestamp_to_description(day_data['dt'], timezone=timezone)['day']}")
                        if day_name.lower() == day_to_search:
                            day_data_block = day_data
                            # print(day_data)
                            break

                    if day_data_block is not None:
                        for hour_data in weather_raw["hourly"]:
                            # day_name = self.timestamp_to_description(hour_data["dt"], timezone=timezone)["day"]
                            day_name = timestamp_to_description(hour_data["dt"], timezone=timezone)["day"]
                            if day_name.lower() == day_to_search:
                                hourly_block.append(hour_data)

                        # print(len(hourly_block))

                        answer = self.__daily_forecast(day_data_block=day_data_block,
                                                       hourly_data_block=hourly_block,
                                                       town_name_to_speak=town_name,
                                                       timezone=timezone)
                    else:
                        answer = f"Nothing found for {day_to_search}."

                    return answer
                else:
                    answer = self.__weekly_forecast(town_name=town_name,
                                                    current_conditions=current_conditions,
                                                    daily_data_list=daily_data_list,
                                                    hourly_data_list=hourly_data_list,
                                                    timezone=timezone,
                                                    another_location=search_for_another_location)
                    return answer

            except KeyError as err:
                print(f"Invalid weather_raw data: {err}")
                return None

            except Exception as err:
                print(err)
                return None
        else:
            print("weather_data could not obtain")
            return None

    def process(self, slots: dict, senses):
        return_msg = None
        answer_expected = None

        status = None
        note = ""

        prior_msg = self.generate_prior_msg(slots)
        yield prior_msg

        if 'ask' in slots.keys():

            # collect if asked for event or for events together:
            events = ['rain', 'thunderstorm', 'drizzle', 'tornado', 'snow']
            asked_for_events = [ev for ev in events if ev in slots['ask']]
            asked_for = ",".join(asked_for_events) if asked_for_events else None

            if 'weather' in slots['ask']:

                # Check if ask is for another location:
                if 'where' in slots.keys():
                    location_data = senses.location.search_location_data(slots['where'])
                    if location_data:
                        # town_name_to_speak = f"in {slots['where']}"
                        town_name_to_speak = f"in {location_data['city']}"
                    else:
                        town_name_to_speak = "outside"
                    # print(location_data)
                else:
                    location_data = None
                    town_name_to_speak = "outside"

                weather_data = None

                if location_data:
                    weather_data = senses.environment.search_for_weather_data(location_data['lat'], location_data['lon'])

                # If we still not found what we search for, we use location 'outside'.
                if not weather_data:
                    try:
                        weather_data = senses.environment.last_environment_data['weather']
                    except:
                        pass

                if weather_data:
                    return_msg = f"The weather {town_name_to_speak} is {weather_data['t'][0]} degrees with {weather_data['conditions']} and {weather_data['wind']}. It feels like {weather_data['t'][1]}. {weather_data['air']} {weather_data['events']}"
                    status = 'complete'
                else:
                    note = "I can't get the weather information Sir. The service may be disconnected."
                    return_msg = note
                    status = "failed"

            elif asked_for is not None:
                location_data = None
                town_name_to_speak = None
                any_rain_answer = None

                if 'where' in slots.keys():
                    location_data = senses.location.search_location_data(slots['where'])
                    if location_data:
                        # town_name_to_speak = f"{slots['where']}"
                        town_name_to_speak = f"{location_data['city']}"

                day_to_search = "today"
                search_for_next = False
                if 'when' in slots.keys():
                    # if there is 'next' in the day name ('next monday'), search for next will become True
                    search_for_next = slots['when'].split()[0] == 'next'
                    # if 'next' in the day name, we remove it, so we use only da day name to search for.
                    day_name = slots['when'].replace('next', '').strip()

                    days_to_search_list = ['tomorrow', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                    day_to_search = day_name if day_name in days_to_search_list else 'today'
                    # After this, if the day to search is "now" or "today" it remains "today", else: day name.

                # print(f"Asked for: {asked_for} | location: {town_name_to_speak}, {location_data} | day: {day_to_search} | asked_for_next: {search_for_next}")

                if location_data:
                    # search for events in another location.
                    return_data = senses.environment.last_weather.get_weather_api(location_data['lat'], location_data['lon'], searching=True)
                    if return_data:
                        weather_raw = return_data[1]
                        # note: return_data = (weather_data, weather_raw); we use weather_raw.
                    else:
                        weather_raw = None
                else:
                    # search in the device location (updated from 'senses' module.
                    weather_raw = senses.environment.last_weather.weather_raw  # we use the instance attribute directly.

                if weather_raw:
                    timezone = pytz.timezone(weather_raw["timezone"])
                    current_conditions = weather_raw['current']['weather'][0]

                    any_rain_answer = self.__extract_bad_weather_events(search_for=asked_for, day_to_search=day_to_search, weather_raw=weather_raw, town_name_to_speak=town_name_to_speak, timezone=timezone)

                if any_rain_answer:
                    return_msg = any_rain_answer
                    status = 'complete'
                else:
                    return_msg = "Sorry Sir, I wasn't able to complete your request. Search failed."
                    note = "It's probably because some missing data."
                    status = 'failed'

            elif 'forecast' in slots['ask']:

                # Check if ask is for another location:
                if 'where' in slots.keys():
                    location_data = senses.location.search_location_data(slots['where'])
                    town_name_to_speak = f"{slots['where']}"
                    # print(location_data)
                else:
                    location_data = None
                    town_name_to_speak = senses.location.city

                day_to_search = None
                search_for_next = False
                if 'when' in slots.keys():
                    # if there is 'next' in the day name ('next monday'), search for next will become True
                    search_for_next = slots['when'].split()[0] == 'next'
                    # if 'next' in the day name, we remove it, so we use only da day name to search for.
                    day_name = slots['when'].replace('next', '').strip()

                    days_to_search_list = ['today', 'tomorrow', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
                                           'saturday', 'sunday']
                    if day_name in days_to_search_list:
                        day_to_search = day_name
                    elif day_name == "now":
                        day_to_search = "today"
                    else:
                        day_to_search = None
                    # day_to_search = day_name if day_name in days_to_search_list else None

                if location_data:
                    latitude = location_data['lat']
                    longitude = location_data['lon']
                    town_name = town_name_to_speak
                else:
                    latitude, longitude = None, None
                    town_name = senses.location.city

                # print(f"town_name={town_name} | day_to_search={day_to_search} | search_for_next={search_for_next} | lat={longitude} | lon={longitude}")

                search_for_another_location = False
                weather_data = None
                weather_raw = None
                if latitude and longitude:
                    # search for events in another location.

                    return_data = senses.environment.last_weather.get_weather_api(latitude, longitude, searching=True)
                    if return_data:
                        weather_data, weather_raw = return_data
                        search_for_another_location = True
                        # note: return_data = (weather_data, weather_raw); we use weather_raw.
                        # we use weather_data to directly get the info for the expected bad weather in the next 48 h, if any
                else:
                    # search in the device location (updated from 'senses' module.
                    if senses.environment.last_weather.weather_raw is not None:
                        weather_raw = senses.environment.last_weather.weather_raw  # we use the instance attribute directly.
                        weather_data = senses.environment.last_weather.weather_data


                forecast_answer = self.get_forecast(weather_data=weather_data,
                                                    weather_raw=weather_raw,
                                                    town_name=town_name,
                                                    day_to_search=day_to_search,
                                                    search_for_next=search_for_next,
                                                    search_for_another_location=search_for_another_location)
                # print(forecast_answer)

                if forecast_answer:
                    return_msg = forecast_answer
                    status = 'complete'
                else:
                    return_msg = "Task failed. Some unknown error returned an empty forecast data."
                    note = "an unknown error returned an empty forecast data."
                    status = 'failed'

            # else:
            #     ...
            #     note = "I have no skill for that request Sir. Not yet."
            #     status = 'failed'

        # It is a valid request. Save it in the memory, along with its completion status...
        memory.add_request(self.INTENT, slots, status=status, note=note)

        yield return_msg, answer_expected


class MusicQueries:
    # Storing the data from the last successful execute
    # If incomplete data received, the response asks if to use the same data as the last time.
    # It may also use a random asking, or choosing the data itself.
    last_completed: dict = None

    @classmethod
    def process(cls, slots: dict, senses, get_same_as_last=False):
        return_msg = None
        answer_expected = None

        if get_same_as_last:
            slots_to_use = cls.last_completed.copy()
        else:
            slots_to_use = slots

        cls.last_completed = slots

        yield return_msg, answer_expected


class General:

    @staticmethod
    def process(slots: dict):
        # is there is answer of a ringing (-sir are you there? - yes /tell me)
        if sig.is_ringing:
            answer_positive = ["what", "what do you want", "tell me", "yes", "shoot", "yes i'm here"]
            answer_negative = ["no", "no i'm not", "not now", "wait", "wait a second", "wait a minute",
                               "wait a few moments", "just a second", "just a moment"]
            answer_me = None

            for ans in answer_positive:
                if ans in slots.values():
                    answer_me = True

            for value in slots.values():
                if value in answer_positive:
                    answer_me = True
                elif value in answer_negative:
                    answer_me = False

            if answer_me is not None:
                if answer_me:
                    # Get all the reports and return them as one message
                    sig.ringing_stop()
                    # use the 'generator version' of reports to speak them all...
                    reports = reporter.get_reports()
                    return_msg = ""
                    for report in reports:
                        # report[0]: element -> dict {'msg', 'about'}
                        # report[1]: elements left -> int
                        if report is not None and isinstance(report[0], dict) and isinstance(report[0]['msg'], str):
                            return_msg += report[0]['msg']

                    return return_msg

                else:
                    return "OK."

        # 1. Skill to REPEAT whet PDA last said...
        say_again_cmd = ["repeat", "what did you say", "excuse me"]
        if ('cmd' in slots.keys() and slots['cmd'] in say_again_cmd) or (
                'ask' in slots.keys() and slots['ask'] in say_again_cmd):
            last_spoken_sentence = memory.get_last_thought()
            if last_spoken_sentence:
                respond_msg = last_spoken_sentence['msg']
                if len(respond_msg) > 50:
                    return f"Sure. {respond_msg}"
                # TODO: how to remove 'Sir' from the end of the sentence if is there
                else:
                    return f"I said {respond_msg}"

        if 'cmd' in slots.keys():
            if 'tell me' in slots['cmd'] or 'shoot' in slots['cmd']:
                return "I didn't say nothing Sir."

        elif 'ask' in slots.keys():

            # return "I didn't say nothing Sir."
            ...

            # TODO: Handle questions related to the last command
            """
            comand status: failed.
            - why / why is that
            - what happen
            - explain
            """
            ...

        return None


class Feedback:
    @staticmethod
    def process(slots: dict):
        # a property that is added to the total mood of Alex (feeling good or bad)
        # If the answer is positive, it returns a positive value, and viceversa...
        mood_points = 0

        return_msg = None

        if 'positive' in slots.keys():
            if 'thank' in slots['positive']:
                chs = ["Always!", "Always Sir.", "Any time Sir.", "You're welcome Sir."]
            # else:
            #     chs = ['Thank you!', 'Thanks!']

                return_msg = random.choice(chs)

        elif 'negative' in slots.keys():
            chs = ["Well, no one is perfect!", "Sorry!", "I'm sorry to hear that."]
            return_msg = random.choice(chs)

        # return return_msg, data_required, mood_points
        return return_msg


class Greetings:
    @staticmethod
    def process(slots: dict):
        return_msg = None
        ...

        return return_msg


# TODO: Alex, go to / initiate / begin the advance mode... As you wish...
#  --> shifting the command mode to free-speak mode (using Whisper and chatGPT API)

# Skill list is filled with the skill class and the skill name.
# This allows the class skill to be directly called from the rest of the code.
SKILL_LIST = {
    'time': TimeQueries,
    'schedule': ScheduleQueries,
    'weather': WeatherQueries,
    'system': SystemQueries,
    'music': MusicQueries,
}

# Usually referred to the latest command (last record in the history)
GENERAL_LIST = {
    'general': General,
    'feedback': Feedback,
    'greeting': Greetings,
}