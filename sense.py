"""
This module contains all the classes and functions
for sensing the environment,
including SPEECH TO TEXT transcription

The Sense functions return a sequence (mostly JSON),
suitable to be analyzed from the brain module
"""

# ======================== IMPORT =========================
import time
from datetime import datetime

# ------ Speech Recognition ------
import wave
import struct

import pvporcupine
import pvrhino
import pvcheetah
from pvrecorder import PvRecorder

# ------ My Libraries ------
from sense_skills import SenseSingleton
from events import Signals as sig

# ======================= GLOBALS =========================


# ---------------------------------------------------------
# ======================= CLASSES =========================

class Senses:

    def __init__(self):
        self.connection = SenseSingleton.get_instance().connection
        time.sleep(5)  # wait the connection class to start its self-updating thread and to update all status info

        self.location = SenseSingleton.get_instance().location
        time.sleep(5)  # wait the location to load, before initializing. The Environment class needs a location.

        # 'self.environment' loads the latest data for the environment (inside and outside)...
        self.environment = SenseSingleton.get_instance().environment
        time.sleep(5)

        # 'self.system' has the latest information about the onboard sensors
        self.system = None

        print("SENSES are loaded successfully.")

    def __del__(self):
        """The SenseSingleton class has a function to delete the Connection and Location instances on program exit."""
        if self.connection is not None:
            del self.connection
        if self.location is not None:
            del self.location
        if self.system is not None:
            del self.system
        if self.environment is not None:
            del self.environment


class Listen:
    __access_key = '...'  # put your picovoice access key here !!!
    __keyword_path = ['sr/porcupine/hey-alex_pi.ppn',
                      'sr/porcupine/alex-you-there_pi.ppn',
                      'sr/porcupine/alex-you-up_pi.ppn',
                      'sr/porcupine/alex-come-up_pi.ppn',
                      'sr/porcupine/good-morning-alex_pi.ppn']  # porcupine wake-word
    __context_path = "sr/alexis.rhn"  # Rhino speech to intend model path. The newest one.
    __model_path = 'sr/alexis.pv'  # cheetah speech-to-text

    def __init__(self):
        self.__is_error = False
        # self.__is_online = SenseSingleton.get_instance().connection.is_internet

        self.status = 'porcupine'  # 'porcupine', 'rhino', 'cheetah'

        self.pc = None
        self.rhino = None
        self.cheetah = None

        try:
            self.pc = pvporcupine.create(access_key=self.__access_key, keyword_paths=self.__keyword_path)
            # rhino = pvrhino.create(access_key=self.__access_key, library_path=None, model_path=None, context_path=self.__context_path, endpoint_duration_sec=3, sensitivity=0.5, require_endpoint=False)
            self.rhino = pvrhino.create(
                access_key=self.__access_key,
                context_path=self.__context_path,
                sensitivity=0.2,  # lower value decrease potentially misunderstandings
                require_endpoint=False,

            )
            # TODO: self.cheetah = ... or Open Ai Whispr

        except Exception as e:
            print(e)
            self.__is_error = True

    def listen_for_wakeword(self):
        keyword_index = -1
        ringing_msg = None
        recorder = None
        try:
            recorder = PvRecorder(device_index=-1, frame_length=self.pc.frame_length)
            recorder.start()

            wav_file = wave.open('pc.wav', "w")
            wav_file.setparams((1, 2, 16000, 512, "NONE", "NONE"))

            print("[Alex: Going Idle...]")
            while not ringing_msg:
                pcm = recorder.read()

                if wav_file is not None:
                    wav_file.writeframes(struct.pack("h" * len(pcm), *pcm))

                keyword_index = self.pc.process(pcm)
                if keyword_index >= 0:
                    # check for each keyword_index (0, 1, 2, 3, 4)
                    break
                else:
                    ringing_msg = sig.get_ringing_msg()

            recorder.stop()

        except Exception as e:
            print(f"Error in porcupine: {e}")
            if recorder is not None:
                recorder.delete()
        finally:
            if recorder is not None:
                recorder.delete()
            return keyword_index, ringing_msg

    # Capturing commands. Uses 2 regimes:
    # 1. Main interaction, using ident='Alex' or ident='Alexandra').
    #   - Active longer time allowing directly speaking the command only by including the name of PDA.
    # 2. Additional interaction, without 'ident' required. Active for short time
    # Note: 'ident' will be checked as a rhino slot.
    def listen_for_cmd(self, silent_timeout, engaged=False):
        recorder = None
        intent, slots = None, None
        ringing_msg = None
        try:
            recorder = PvRecorder(device_index=-1, frame_length=self.rhino.frame_length)
            silent_time = time.time()

            recorder.start()
            while not ringing_msg:
                # note: if a ringing occur, the loop will break and PDA will return the response.
                pcm = recorder.read()
                is_finalized = self.rhino.process(pcm)
                if is_finalized:
                    inference = self.rhino.get_inference()
                    if inference.is_understood:

                        intent = inference.intent
                        slots = inference.slots

                        print(f"YOU: intent={intent} | slots={slots}")

                        # if not engaged, in order to react, it needs an 'Alex'/'Alexandra' keyword in the message.
                        if not engaged:
                            if 'id' in slots.keys() and 'alex' in slots['id'].lower():
                                # note: this will be also valid if 'Alexandra' is spoken
                                break
                            else:
                                continue
                        else:
                            break

                    else:
                        if time.time() - silent_time >= silent_timeout:
                            break  # exit if nothing is understood for 10 minutes. This will cause the Ai to go-sleep

                    ringing_msg = sig.get_ringing_msg()

            recorder.stop()

        except Exception as e:
            print(e)
            self.__is_error = True
            if recorder is not None:
                recorder.delete()

        finally:
            if recorder is not None:
                recorder.delete()

        return intent, slots, ringing_msg

    # use this method to clear the resources taken from Porcupine, Rhino and Cheetah
    def clear_picovoice_res(self):
        if self.pc is not None:
            self.pc.delete()

        if self.rhino is not None:
            self.rhino.delete()

        if self.cheetah is not None:
            self.cheetah.delete()

        if not self.pc and not self.rhino and not self.cheetah:
            print("Picovoice resources cleared successfully.")
