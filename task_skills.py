
# all the task related skills that ALEX can do, are written here.
"""
Skills classes have a function to take "what/where/when/where" input from 'Respond' class
and activate the skill needed. Then the skill returns data, which is returned to the user.
"""

"""
1. Time and alarm:
- what's the time
- what time is it
- is there any alarm set (for tomorrow)
- set an alarm for 7 am tomorrow
- (could you) wake me up at 7am tomorrow
- (alex) set an alarm at same time tomorrow

2. Music:
- rock and roll (please)
- drop my needle
- could you play some hiphop
- play some music for my soul

3. Weather:
- what's the weather outside
- what's the temperature outside
- what's the conditions in the room
- is there any rain (unusual conditions) expected
- what's the forecast for tomorrow
"""
import datetime
import time
from collections import deque
from events import Signals as sig
from events import EventReporter as reporter

from brain import ConversationMemory as memory

import random
# from abc import ABC, abstractmethod


class Messages:
    """
    Used to generate a messages to user, during the task processing.
    For example, some methods will return a prior message like 'Ok', 'Sure!', 'Of course!' before the process starts.
    """
    @staticmethod
    def generate_prior_msg(slots):
        # if 'preq' in slots.keys():
        #     if 'can you' in slots['preq'] or 'could you' in slots['preq']:
        #         chs = ["Of course!", "Sure.", "Yes.", "Absolutely!", "I'd be delighted to.", "Certainly!"]
        #         return random.choice(chs)
        # elif 'cmd' in slots.keys():
        #     chs = ["Sure.", "OK.", "Sir!", "Yes Sir."]
        #     return random.choice(chs)
        # return ""

        if 'preq' in slots.keys():
            preq_list1 = ["tell me", "give me", "i want"]
            preq_list2 = ["have you got", "do you know", "can you"]
            preq_list3 = ["can i have", "may i have"]

            if 'could you' in slots['preq']:
                chs = ["Of course!", "I'd be delighted to.", "Yes."]
                return_msg = random.choice(chs)
            elif slots['preq'] in preq_list1:
                chs = ["OK.", "Of course!", "Yes Sir.", "Sure."]
                return_msg = random.choice(chs)
            elif slots['preq'] in preq_list2:
                chs = ["Yes.", "I do Sir."]
                return_msg = random.choice(chs)
            elif slots['preq'] in preq_list3:
                chs = ["Always Sir!", "Of course!", "Sure.", "Absolutely!", "Certainly!"]
                return_msg = random.choice(chs)
            else:
                return_msg = None

            return return_msg

        elif 'cmd' in slots.keys():
            chs = ["Sure.", "OK.", "Sir!", "Yes Sir."]
            return random.choice(chs)

        return None


class SystemQueries(Messages):
    """
    Used for processing system queries like 'shut down', 'get onboard sensors', etc.
    """
    INTENT = 'system'
    status_list = ['completed', 'answer-expected', 'canceled', 'failed']

    # This will help to process the request if incifficient data provided.
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
        cls.history.append(slots_data)

    @classmethod
    def get_most_used_from_history(cls):
        # TODO:This method will get the most used slots needed for an operation to be executed
        ...

    def process(self, slots: dict, senses):
        print(f"slot_to_use in SystemQueries.process(): {slots}")
        # print(f"History = {self.get_history_last()}")
        """
        This function needs:
        - keys: 'cmd', 'ask'
        - cmd: 'shutdown'
        - ask: 'battery, battery status, battery charge, charge, core temperature
        """
        # TODO: Save the slots to history:
        # self.append_to_history(slots)

        if 'cmd' in slots.keys():
            if 'shutdown' in slots["cmd"]:
                return_msg = None
                status = None
                note = None
                if 'positive' in slots.keys():
                    chs = ['OK.', 'All right!']
                    return_msg = f"{random.choice(chs)} Shutting down..."
                    status = self.status_list[0]

                    self.__shutdown()

                elif 'negative' in slots.keys():
                    return_msg = "Shutting down cancelled."
                    status = self.status_list[0]

                else:
                    # return a question for confirmation:
                    chs = ["Are you sure?", "Please confirm."]
                    return_msg = f"Preparing to shutdown... {random.choice(chs)}"
                    status = self.status_list[1]
                    note = "You requested a shutdown. I asked for confirmation."

                # It is a valid request. Save it in the memory, along with its completion status...
                memory.add_request(self.INTENT, slots, status=status, note=note)
                # Also save it in the TASK history, for eventually later use
                self.append_to_history(slots_data=slots)

                yield return_msg, status, note

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
        respond_msg = ""  # message to be spoken
        status = None  # status, telling if success or failde
        note = None  # if failed or cancelled, here will be the reason.
        # 1. Returning a prior (init) message to user, to identify that the function will be executed:
        prior_msg = self.generate_prior_msg(slots)
        yield prior_msg

        try:
            if 'ask' in slots.keys() and ('preq' in slots.keys() or 'what' in slots['ask']):
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

                    day_name_to_speak = 'today'
                    dt_today = datetime.datetime.now(senses.location.timezone)

                    if 'day' in slots.keys():
                        ...
                    if 'tomorrow' in slots['ask'] or 'tomorrow' in slots.values():
                        dt_today = datetime.datetime.now(senses.location.timezone)
                        dt = dt_today + datetime.timedelta(days=1)
                        day_name_to_speak = 'tomorrow'
                    else:
                        dt = datetime.datetime.now(senses.location.timezone)

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

                    msg_list = [f"{day_name_to_speak} is {weekday}, {day_phrase} of {month}.", f"It's {weekday}, {day_phrase} of {month} Sir.", f"{weekday}, {day_phrase} of {month}."]
                    respond_msg = random.choice(msg_list)
                    status = 'completed'

                    memory.add_request(self.INTENT, slots, status=status, note=note)

                # else:
                #     respond_msg = "I can't answer Sir."
                #     status = 'failed'
                #     note = 'because of incomplete request input'
        except Exception as e:
            print(e)
            respond_msg = "I can't respond to that Sir."
            status = 'failed'
            note = 'because an unexpected error occur'


        yield respond_msg, status, note

        # TODO: a 'wake me up at..' skill in time_query.


class ScheduleQueries(Messages):
    ...


class WeatherQueries(Messages):

    # def generate_prior_msg(self, slots):
    #     # NOTE: This is an ABSTRACT METHOD from class Messages. Do not touch it, unless you want to update it.
    #     ...

    def process(self, slots: dict, senses):
        return_msg = None
        status = None
        note = ""

        prior_msg = self.generate_prior_msg(slots)
        yield prior_msg

        if 'ask' in slots.keys() and 'preq' in slots.keys():

            is_there = ['is there', 'is there any', 'any']
            whats = ["what's", "tell me", "how's", "could you tell me", "give me"]

            # collect if asked for event or for events together:
            events = ['rain', 'thunderstorm', 'drizzle', 'tornado', 'snow']
            asked_for_events = [ev for ev in events if ev in slots['ask']]
            asked_for = ",".join(asked_for_events) if asked_for_events else None

            if 'weather' in slots['ask'] and slots['preq'] in whats:  # 'How's the weather outside?'

                # Check if ask is for another location:
                if 'where' in slots.keys():
                    location_data = senses.location.search_location_data(slots['where'])
                    if location_data:
                        town_name_to_speak = f"in {slots['where']}"
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
                    status = "failed"

            elif asked_for is not None and slots['preq'] in is_there:  # 'Is there any rain expected today?'
                location_data = None
                town_name_to_speak = None
                if 'where' in slots.keys():
                    location_data = senses.location.search_location_data(slots['where'])
                    if location_data:
                        town_name_to_speak = f"{slots['where']}"


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
                    any_rain_answer = senses.environment.last_weather.search_for_events(asked_for, day_to_search=day_to_search, search_for_next=search_for_next, latitude=location_data['lat'], longitude=location_data['lon'], town_name_to_speak=town_name_to_speak)
                else:
                    any_rain_answer = senses.environment.last_weather.search_for_events(asked_for, day_to_search=day_to_search, search_for_next=search_for_next)

                if any_rain_answer:
                    return_msg = any_rain_answer
                    status = 'complete'
                else:
                    note = "Search failed. It's probably because some missing data."
                    status = 'failed'

            elif 'forecast' in slots['ask'] and slots['preq'] in whats:

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
                forecast_answer = senses.environment.last_weather.get_forecast(town_name=town_name, day_to_search=day_to_search, search_for_next=search_for_next, latitude=latitude, longitude=longitude)
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

        yield return_msg, status, note


class MusicQueries:
    # Storing the data from the last successful execute
    # If incomplete data received, the response asks if to use the same data as the last time.
    # It may also use a random asking, or choosing the data itself.
    last_completed: dict = None

    @classmethod
    def process(cls, slots: dict, senses, get_same_as_last=False):
        return_msg = None
        status = None
        note = ""

        if get_same_as_last:
            slots_to_use = cls.last_completed.copy()
        else:
            slots_to_use = slots

        if status == 'completed':
            cls.last_completed = slots

        yield return_msg, status, note

class NewsQueries:
    def process(self, slots: dict, senses):
        return_msg = None
        status = None
        note = ""

        """
        Could you update us/me
        Colud you give me an updates?
        Whats new?
        """
        # The processor will get BASIC weather info, sensor info, one HEAD NEWS, Something related to trash...

        yield return_msg, status, note


# =================== GENERAL QUERIES PROCESSING... ===================

class GeneralQueries:
    """
    The class has a functionality to yield an initial message to be spoken to the user
    """
    @staticmethod
    def process(slots: dict):

        # is there is answer of a ringing (-sir are you there? - yes /tell me)
        if sig.is_ringing:
            answer_positive = ["what", "what do you want", "tell me", "yes", "shoot", "yes i'm here"]
            answer_negative = ["no", "no i'm not", "not now", "wait", "wait a second", "wait a minute", "wait a few moments", "just a second", "just a moment"]
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
        if ('cmd' in slots.keys() and slots['cmd'] in say_again_cmd) or ('ask' in slots.keys() and slots['ask'] in say_again_cmd):
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
            if 'what' in slots['ask'] or 'what do you want' in slots['ask']:
                return "I didn't say nothing Sir."

            # TODO: Handle questions related to the last command
            """
            comand status: failed.
            - why / why is that
            - what happen
            - explain
            """
            ...

        return None


class Greetings:
    @staticmethod
    def process(slots: dict):
        return_msg = None
        ...

        return return_msg


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
            else:
                chs = ['Thank you!', 'Thanks!']

            return_msg = random.choice(chs)

        elif 'negative' in slots.keys():
            chs = ["Well, no one is perfect!", "Sorry!", "I'm sorry to hear that."]
            return_msg = random.choice(chs)

        # return return_msg, data_required, mood_points
        return return_msg


# TODO: Alex, go to / initiate / begin the advance mode... As you wish...
#  --> shifting the command mode to free-speak mode (using Whisper and chatGPT API)

# Referred only to a specific skill.
SKILL_LIST = {
    'time': TimeQueries,
    'schedule': ScheduleQueries,
    'weather': WeatherQueries,
    'system': SystemQueries,
    'music': MusicQueries,
    'news': NewsQueries,
}

# Usually referred to the latest command (last record in the history)
GENERAL_LIST = {
    'general': GeneralQueries,
    'feedback': Feedback,
    'greeting': Greetings,
}

# -- ANSWERS left. They will be checked separately.

