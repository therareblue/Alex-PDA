"""
About:
Module containing all functions to generate a user-friendly response
Here the Speech functionality is implemented, an API from Google texttospeech
"""
import datetime
# ======================== IMPORT =========================
import time

import os
import random
import signal

import threading

from tools import encode_str

# ----- Speech ----
from google.cloud import texttospeech_v1

from sense_skills import SenseSingleton
# from task_skills import SKILL_LIST, GENERAL_LIST
from task_skills_v2 import SKILL_LIST, GENERAL_LIST

from events import Signals as sig
from brain import ConversationMemory as memory
# from events import EventReporter as reporter


# ====================== GLOBAL VARs ======================
os.umask(0)  # this os command gives a read/write and execute permission to the user running the script

titles = ["Todor", "Sir", "Boss"]


# ---------------------------------------------------------
# ======================== SPEAK ==========================
"""
Speech.speak() has an attribute 'about', tracking what the message is all about. 
There are the following 'about' categories:
- general (default)
- system
- location
- alarm / ringing
....
The speak is mostly used from the 'Response.respond()' method, where an 'intent' is available.
This can be returned along with the response message, in order to be used from the speech class.

"""


class TimeOutException(Exception):  # used in alarm_handler below
    pass


def alarm_handler(signum, frame):  # used in class Speech
    print("ALARM signal received")
    raise TimeOutException()


class Speech:
    # --- class attributes ---
    VOICE0 = texttospeech_v1.VoiceSelectionParams(language_code='en-US', name='en-US-Wavenet-F', ssml_gender=texttospeech_v1.SsmlVoiceGender.FEMALE)
    VOICE1 = texttospeech_v1.VoiceSelectionParams(language_code='en-US', name='en-US-Neural2-F', ssml_gender=texttospeech_v1.SsmlVoiceGender.FEMALE)

    client = None

    def __init__(self):
        # --- Instance attributes ---
        self.__is_error = False

        #  constantly updated parameter, keeping information if there is an internet connection or not.
        # self.is_online

        try:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "gtts_accnt.json"
            self.client = texttospeech_v1.TextToSpeechClient()
            print("TTS account is now active.")

        except Exception as e:
            print(f"An exception raised: {e}")
            self.__is_error = True  # if any error in tts init rise, a flag arise.;

        print(f"is_online = {self.is_online}")
        print(f"is_error = {self.__is_error}")

        # self.memory = ConversationMemory  # Pointer to class ConversationMemory. Used to save all output (spoken) thoughts.

    @property
    def is_online(self):
        return SenseSingleton.get_instance().connection.is_internet

    @staticmethod
    def __speak_offline(text):  # this method is not accessed outide of the class
        try:
            # check if a file to speak (with name "text") is available offline
            encoded = encode_str(text)
            filename = f"offline_audio/{encoded}.mp3"
            # print(f"try to speak: {filename}")
            path = f"/home/alex/lab/alex2.0/{filename}"
            is_exist = os.path.exists(path)
            # print(f"The file: {path} exists = {is_exist}")
            if is_exist:
                os.system("mpg123 -q '" + filename + "'")
                # os.system("mpg321 '" + filename + "' --stereo")
                # print(f"ALEX: {text} | speak_online=False")
                return True
            else:
                return False

        except Exception as e:
            print(f"ERR: in __speak_offline(): {e}")

    def __speak_online(self, text, voice, rate, save_it=False):
        if not self.__is_error and self.is_online:
            self.audio_config = texttospeech_v1.AudioConfig(audio_encoding=texttospeech_v1.AudioEncoding.MP3, speaking_rate=rate)
            if voice == 1:
                voice_to_use = self.VOICE1
            else:
                voice_to_use = self.VOICE0

            # Note: The Ubuntu max file_name is 255. So with the encoding it should not exceed that.
            if save_it and len(text) < 60:
                encoded = encode_str(text)
                filename = f"offline_audio/{encoded}.mp3"
            else:
                filename = "speak.mp3"

            # the following is used to raise a timeout exception if the response takes too long
            signal.signal(signal.SIGALRM, alarm_handler)
            signal.alarm(3)

            try:
                synthesis_input = texttospeech_v1.SynthesisInput(text=text)
                response = self.client.synthesize_speech(input=synthesis_input, voice=voice_to_use, audio_config=self.audio_config)

            except Exception as e:
                print(f"ERR: in __speak_online(): {e}")
                signal.alarm(0)
                return False

            else:
                signal.alarm(0)
                # print(f"ALEX: {text} | rate={rate} | speak_online=True")

                with open(filename, 'wb') as output:
                    output.write(response.audio_content)
                os.system("mpg123 -q '" + filename + "'")
                # os.system("mpg321 '" + filename + "' --stereo")
                return True
        else:
            return False

    @staticmethod
    def __disconnected_prompt():
        os.system("mpg123 -q 'disconnected.mp3'")
        # os.system("mpg321 'disconnected.mp3'")
        print("ALEX: Sorry! My speech engine is disconnected.")

    def speak(self, text, about='general', msg_type='say', voice=0, rate=0.9, save_it=True, try_offline=True):
        if text:
            if try_offline:

                # first try offline and if not found, then try online. If not found: say "disconnected".
                if self.__speak_offline(text):
                    memory.add_thought(text, about, msg_type)
                elif self.__speak_online(text, voice, rate, save_it):
                    memory.add_thought(text, about, msg_type)
                else:
                    self.__disconnected_prompt()

            else:

                # first try online and if no connection, then try offline. If not found: say "disconnected".
                if self.__speak_online(text, voice, rate, save_it):
                    memory.add_thought(text, about, msg_type)
                elif self.__speak_offline(text):
                    memory.add_thought(text, about, msg_type)
                else:
                    self.__disconnected_prompt()


# the class contains functions to generate a response string from some data.
class Response(Speech):

    __CONV_HISTORY_LIMIT = 10
    __MAX_ATTEMPT_LIMIT = 2  # limits the number of attempting to execute a TASK, when data is not enough

    def __init__(self, senses):
        # Response will need to speak itself, so the speak() should be available here as well.
        super().__init__()

        self.__senses = senses

        # answer_expected is a dictionary that fills with question if an answer is expected...
        self.answer_expected = None  # {'intent': 'system', 'init-slots':{} 'question': 'I need confirmation to shut down the system.'}

    def expectation_clear(self):
        """Method used from AlexAPI to clear the expectations, if for example alex go to sleep..."""
        self.answer_expected = None
        sig.ringing_stop()
        # self.speak('whatever...')

    @staticmethod
    def greeting_respond(hour, incoming=True):
        # incoming is a value True for "hello" or false for "goodbye"
        # decode=["morning", "noon", "afternoon", "evening", "night", "midnight"]

        now_is = hour
        if incoming:
            decode = ["Good morning", "Hello", "Good afternoon", "Good evening", "Good evening", "Good morning"]
        else:
            decode = ["Have a good day", "Have a good day", "Have a good afternoon", "Have a good evening",
                      "Good night", "Good night"]
        if 4 < now_is <= 10:
            return decode[0]
        elif 10 < now_is <= 12:
            return decode[1]
        elif 12 < now_is <= 18:
            return decode[2]
        elif 18 < now_is <= 22:
            return decode[3]
        elif now_is in [23, 0, 1, 2]:
            return decode[4]
        elif 2 < now_is <= 4:
            return decode[5]

    @staticmethod
    def wakeup_response(wake_word_index, timezone=None):
        """
        Used when with Porcupine wake-word capturing.
        The method generates response from giving 'wake_word_index'
        The corresponding index is generated when Porcupine detects a wake-word. See 'class Listen' for details.
        """
        if wake_word_index == 0:
            chs = ["Hey?", "Sir?", "Boss?", "Tell me?"]
            return random.choice(chs)
        elif wake_word_index == 1:
            chs = ["Always!", "I'm here?", "Sir?", "Always Sir.", "Yes."]
            return random.choice(chs)
        elif wake_word_index == 2:
            chs = ["At your service Sir.", "At your service!", "Always Sir."]
            return random.choice(chs)
        elif wake_word_index == 3:
            chs = ["At your service Sir.", "What can I do for you?", "Tell me?"]
            return random.choice(chs)
        elif wake_word_index == 4:
            hour = datetime.datetime.now(timezone).hour
            if hour > 11:
                return "Hello Sir."
            else:
                chs = ["Good morning Sir!", "Good morning!", "Good morning Sir?"]
                return random.choice(chs)
        else:
            return False

    def task_process(self, intent_to_use, slots_to_use, task):
        if task is not None and slots_to_use is not None:
            # Task is attempting to process the request...
            processor = task.process(slots_to_use, senses=self.__senses)

            for return_data in processor:
                if return_data and isinstance(return_data, str):
                    # if return_data is a string message, it means it is a prior (init) message
                    self.speak(return_data, about=intent_to_use)

                elif return_data and isinstance(return_data, tuple):

                    # return_data is the final answer, containing message and answer_expected dict, if any...
                    return_msg, self.answer_expected = return_data
                    if return_msg:
                        if self.answer_expected is not None:
                            self.speak(return_msg, about=intent_to_use, msg_type='ask')

                            # note: an answer is expected. so ringing starts to engage the user:
                            sig.ringing_start('answer-expected')
                        else:
                            self.speak(return_msg, about=intent_to_use)

                        return True

                    else:
                        self.speak("Sorry Sir, I wasn't able to complete your request.", about=intent_to_use)


            # Note: There may be a TASK functions with no 'prior'/'init' message, but only a final answer.
            # Written this way, the above script handles one, many or none init messages, and the final answer.

        else:
            print(f"No associated task for: {intent_to_use}.")

        return False

    """
    1. IF RINGING: 
    - the RESPOND function only respond if the answer is in ["tell me", "what", "shoot"...] 
    """
    def respond(self, intent, slots):
        # print(f"intent = {intent} | slots = {slots}")
        # print(f"Answer expected: {self.answer_expected} | ringing: {sig.is_ringing}")

        # 1. Trim the request, removing the unnecessary 'id' key:
        if "id" in slots.keys():
            slots.pop("id")

        # 1. Check if an answer is expected
        if self.answer_expected is not None:
            if sig.is_ringing:
                """
                1. last request will be ONLY from the TASK skills
                2. if incoming intent == intent from the ringing message and == intent from memory, 
                    - if a confirmation is expected, confirm it
                    - if not, ask again and restart the ringing
                3. if intent is from Task skills but not GENERAL, cancel the answer_expected and porceed to use the new request.
                4. if intent is from GENERAL, add the slots to the one of history and send it to the task from answer_expected['intent']
    
                """

                # --1. get the last intent from history and assign a TASK
                last_request = memory.get_last_request()
                # print(f"last history item = {last_request}")

                if last_request is not None:
                    intent_from_memory = last_request["intent"]
                    slots_from_memory = last_request["slots"]
                else:
                    intent_from_memory = None,
                    slots_from_memory = None

                task = None
                slots_to_use = slots.copy()
                intent_to_use = None

                if intent == "general":
                    # --2. Assign a SKILL based on the intent from the 'answer_expected'

                    # Handle 'what do  you want'/'not now' when answer is expected...
                    ask_list1 = ["what", "what do you want"]
                    if 'ask' in slots.keys():
                        if slots['ask'] in ask_list1:
                            if 'note' in self.answer_expected:
                                self.speak(self.answer_expected['note'])
                                return True
                        elif 'not now' in slots.values():
                            self.expectation_clear()
                            chs = ["OK.", "OK then!"]
                            self.speak(random.choice(chs))
                            return True

                    if 'intent' in self.answer_expected.keys() and self.answer_expected['intent'] is not None:
                        intent_to_use = self.answer_expected['intent']
                        # slots_to_use.update(slots)
                        # If intent_to_use == intent from memory, get the new slots and append those from memory:
                        if intent_to_use == intent_from_memory and slots_from_memory is not None:
                            slots_to_use.update(slots_from_memory)
                        # else slots will be only the slots from the request.

                        if intent_to_use in SKILL_LIST.keys():
                            task = SKILL_LIST[intent_to_use]()

                elif intent in SKILL_LIST.keys():

                    intent_to_use = intent
                    slots_to_use = slots.copy()

                    task = SKILL_LIST[intent_to_use]()

                if task is not None:
                    # Stop the ringing process and clear the expectations
                    self.expectation_clear()
                    # Attempting to process the task...
                    if self.task_process(intent_to_use=intent_to_use, slots_to_use=slots_to_use, task=task):
                        return True
            else:
                self.expectation_clear()
                # NOTE: attempts for an answer is handled by the 'events.ringing' processor.
                # If ringing limit exceeded, it stops, and if is not ringing, it also clears self.answer_expected.

        # Answer is NOT expected. The user request came out of nothing.
        else:
            # 2. Check what kind of intent was received
            if intent in SKILL_LIST.keys():
                # a) The intent is a regular request for a known SKILL
                # -- it uses self.__senses to get the information.
                # -- for now it does not need information from the memory, so it is not used.
                intent_to_use = intent
                slots_to_use = slots.copy()
                task = SKILL_LIST[intent_to_use]()

                # Attempting to process the task...
                if self.task_process(intent_to_use=intent_to_use, slots_to_use=slots_to_use, task=task):
                    return True

            elif intent in GENERAL_LIST.keys():
                # b) The intent is a general request.
                task = GENERAL_LIST[intent]
                slots_to_use = slots.copy()

                if task is not None and slots_to_use is not None:
                    # Processing the request... NOTE: the request only returns one answer, so we use it directly.
                    # doit_again_cmd = ["do it again", "repeat the last command", "lets try again", "try again", "do it one more time"]
                    # if intent == 'general' and 'cmd' in slots.keys() and slots['cmd'] in doit_again_cmd:
                    #     # User requested a do-again command.
                    #     # Note: its logic is a bit different from other general requests...
                    #
                    #     # 1. Get the last from memory:
                    #     last_request = memory.get_last_request()
                    #     # print(f"Attempting to do again: {last_request}")
                    #
                    #     if last_request is not None:
                    #         intent_from_memory = last_request["intent"]
                    #         slots_from_memory = last_request["slots"]
                    #
                    #         if intent_from_memory in SKILL_LIST.keys():
                    #             chs = ["I can do that", "Sure.", "Of course!"]
                    #             self.speak(random.choice(chs))
                    #
                    #             intent_to_use = intent_from_memory
                    #             slots_to_use = slots_from_memory.copy()
                    #             task = SKILL_LIST[intent_to_use]()
                    #
                    #             # Attempting to process the task...
                    #             if self.task_process(intent_to_use=intent_to_use, slots_to_use=slots_to_use, task=task):
                    #                 return True
                    #
                    #     self.speak("Sorry Sir, your last request was not related to any of my skills.")
                    #     return False
                    # else:
                    #     # whether the request is general, feedback or greeting, the processor returns one message.
                    #     return_msg = task.process(slots_to_use)
                    #     if return_msg and isinstance(return_msg, str):
                    #         self.speak(return_msg, about=intent)
                    #
                    #         return True

                    return_msg = task.process(slots_to_use)
                    if return_msg and isinstance(return_msg, str):
                        self.speak(return_msg, about=intent)
                        return True


        return False

