import datetime

from statistics import mean

import pytz
# tz = pytz.timezone('Europe/Sofia')
tz = pytz.timezone('Europe/London')
# get the list of pytz timezones:
# list_of_tz = pytz.all_timezones
# list_short = pytz.common_timezones
# import datetime
# import pytz
# from tzwhere import tzwhere
#
# tzwhere = tzwhere.tzwhere()
# timezone_str = tzwhere.tzNameAt(37.3880961, -5.9823299) # Seville coordinates
# timezone_str
# #> Europe/Madrid
#
# timezone = pytz.timezone(timezone_str)
# dt = datetime.datetime.now()
# timezone.utcoffset(dt)
# #> datetime.timedelta(0, 7200)

"""
ABOUT THIS MODULE:
In the tools.py module are all the functions, used to support the logic and calculations of the other modules.
Placed here, it can be used in multiply modules, preventing duplicates.
"""


# ============== an alternative of Arduino map() function. =================
def map_it(input_value, input_min, input_max, output_min, output_max):
    """Function to transform a value from one input range to another
    - Works like the Arduino map() function
    """
    output_value = ((input_value - input_min) / (input_max - input_min)) * (output_max - output_min) + output_min
    return output_value


# ============== Encode / Decode string for saving offline_audio files =================
def encode_str(text):
    enc = [".", "?", "!", " ", "'", ",", ":", "-"]
    dec = ["_a_", "_b_", "_c_", "_d_", "_e_", "_f_", "_g", "_h_"]

    text2 = text
    for c in text:
        if c in enc:
            index = enc.index(c)
            n = dec[index]
            text2 = text2.replace(c, n)
    return text2


def decode_str(text):
    enc = [".", "?", "!", " ", "'", ",", ":", "-"]
    dec = ["_a_", "_b_", "_c_", "_d_", "_e_", "_f_", "_g", "_h_"]

    text2 = text
    for code in dec:
        if text2.find(code) != -1:
            index = dec.index(code)
            n = enc[index]
            text2 = text2.replace(code, n)
    return text2


# ============ FUNCTIONS FOR HELPING WEATHER AND TIME RESPONSE ===============
# get time with TODAY/TOMORROW / Weekday stamp

def timestamp_to_friendly_time(tmstamp, timezone=None):
    if timezone:
        dt = datetime.datetime.fromtimestamp(tmstamp, timezone)
        dt_now = datetime.datetime.now(timezone)
    else:
        dt = datetime.datetime.fromtimestamp(tmstamp)
        dt_now = datetime.datetime.now()
    wk_day = datetime.datetime.weekday(dt)
    # hr = datetime.datetime.hour(dt)
    hr = int(datetime.datetime.strftime(dt, '%I'))
    mnt = datetime.datetime.strftime(dt, '%M')
    ampm = datetime.datetime.strftime(dt, "%p")
    wk_decode = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    # noon_dec = {"morning": 8, "noon": 12, "lunch": 12, "afternoon": 16, "evening": 20}
    days = int(datetime.datetime.strftime(dt, '%j'))  # return day of the year 0-365
    days_now = int(datetime.datetime.strftime(dt_now, '%j'))
    if days == days_now:
        day_name_decode = 'today'
    elif abs(days - days_now) == 1:
        day_name_decode = 'tomorrow'
    else:
        day_name_decode = wk_decode[wk_day]

    return {'weekday': day_name_decode, 'hours': hr, 'minutes': mnt, 'ampm': ampm}


def timestamp_to_description(timestamp, timezone=None):
    if timestamp and isinstance(timestamp, int):
        # today = datetime.date.today()
        today = datetime.datetime.now(tz=timezone).date()

        dt = datetime.datetime.fromtimestamp(timestamp, tz=timezone)
        day_descr = date_description(dt.day, dt.month)

        # print(f"Obtaining time data: today={today} | asked_for = {dt.date()}")
        if dt.date() == today:
            return {"hour": f"{dt.strftime('%-I %p')}", "day": "today", "day-descr": day_descr}
        elif dt.date() == today + datetime.timedelta(days=1):
            return {"hour": f"{dt.strftime('%-I %p')}", "day": "tomorrow", "day-descr": day_descr}
        else:
            return {"hour": f"{dt.strftime('%-I %p')}", "day": f"{dt.strftime('%A').lower()}", "day-descr": day_descr}
    return None


def date_description(day, month):
    """Generates date string based of the day and month
    for example: '21st of May', '13th of January' ...
    """
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

    return f"{day_phrase} of {month}"


def overal_list_trend(list_of_numbers):
    """Method to determine the overall trend (increasing or decreasing) of a list of numbers.
    It returns a 'strength' of the trend (if increasing, is it large or little increase).
    """
    list_len = len(list_of_numbers)
    if list_len <= 1:
        return 0

    # 1. Split the list by two parts:
    # TODO: Split the list to as much parts as its length, so large lists will be divided by more parts.
    mid = list_len // 2
    first_half = list_of_numbers[:mid]
    second_half = list_of_numbers[mid:]

    # 2. Get each part's mean()
    # mean_first_half = sum(first_half) / len(first_half)
    # mean_second_half = sum(second_half) / len(second_half)
    mean_first_half = mean(first_half)
    mean_second_half = mean(second_half)

    # 3. Calculate the 'weight' of every half. It determines the strength of the part's increasing/decreasing
    first_part_weight = mean_first_half - first_half[0]
    second_part_weight = mean_second_half - second_half[0]

    # 4. Calculate the strength of all the list. If negative, it is decreasing, if positive, it is increasing:
    trend = first_part_weight + second_part_weight
    trend = round(trend, 2)

    return trend


def wind_decode(speed:float, deg:int, return_short:bool=False):
    """Function to generate a message,
    based on wind speed ('speed') and wind direction ('deg')
    - Used both in sense_skills and in task_skills in help of Weather functions.
    """
    # w_description = ""
    w_dir = ''  # , coming from North.
    if deg > 349 and deg <= 360 or deg >= 0 and deg <= 11: w_dir = 'North'
    elif deg > 11 and deg <= 34: w_dir = 'North North East'
    elif deg > 34 and deg <= 56: w_dir = 'North East'
    elif deg > 56 and deg <= 79: w_dir = 'East North East'
    elif deg > 79 and deg <= 101: w_dir = 'East'
    elif deg > 101 and deg <= 124: w_dir = 'East South East'
    elif deg > 124 and deg <= 146: w_dir = 'South East'
    elif deg > 146 and deg <= 170: w_dir = 'South South East'
    elif deg > 170 and deg <= 191: w_dir = 'South'
    elif deg > 191 and deg <= 214: w_dir = 'South South West'
    elif deg > 214 and deg <= 236: w_dir = 'South West'
    elif deg > 236 and deg <= 259: w_dir = 'West South West'
    elif deg > 259 and deg <= 281: w_dir = 'West'
    elif deg > 281 and deg <= 304: w_dir = 'West North West'
    elif deg > 304 and deg <= 326: w_dir = 'North West'
    elif deg > 326 and deg <= 349: w_dir = 'North North West'

    if not return_short:
        if speed == 0: w_description = "no wind"
        # the wind speed is in m/s
        elif speed > 0 and speed <= 5: w_description = f"light breeze coming from {w_dir}"
        elif speed > 5 and speed <= 10: w_description = f"moderate wind coming from {w_dir}"
        elif speed > 10 and speed <= 20: w_description = f"strong wind coming from {w_dir}"
        elif speed > 20: w_description = f"storm wind coming from {w_dir}"
        else: w_description = "no wind"
    else:
        if speed == 0: w_description = "no wind"
        elif 0 < speed <= 5:
            if "East" in w_dir:
                w_description = "eastern light breeze"
            elif "North" in w_dir:
                w_description = "northern light breeze"
            else:
                w_description = "light breeze"
        elif 5 < speed <= 10:
            if "North" in w_dir:
                w_description = "moderate winds from north"
            else:
                w_description = "moderate wind"

        elif 10 < speed <= 20:
            if "North" in w_dir:
                w_description = "strong winds from north"
            else:
                w_description = "strong winds"
        elif speed > 20:
            if "North" in w_dir:
                w_description = "stormy winds from north"
            else:
                w_description = "stormy winds"
        else:
            w_description = "no wind"

    return w_description

# -------------- Raise a time out exception ---------------

# ---------------------------------------------------------