"""
Main file, containing the Artificial User Interface.
"""
# ======================== IMPORT ============================
import time

from respond import Response
from sense import Senses, Listen

from events import Signals as sig
from events import EventReporter as reporter

from threading import active_count


# ====================== MAIN CLASS ==========================
class AlexAPI(Listen, Response):
    # confidence changing from 0 to 100%, representing how 'sure' the PDA is in the command..
    # If confidence does not exceed the threshold, it will ask for more information.
    # __CONFIDENCE_THRESHOLD = 80  # if confidence level is less, Alex asks for additional info.
    # __GIBBERISH_THRESHOLD = 30  # if confidence level is less, the request is treated as a gibberish.

    __GIBBERISH_LIMIT = {
        'engaged': 2,
        'disengaged': 5,
    }

    __MODE_TIMEOUT = {
        'engaged': 20,
        'disengaged': 60,
        'expect': 30
    }

    def __init__(self):
        # print("Instancing Senses...")
        self.senses = Senses()  # get all sensors and their methods.

        # print("Initializing Listen...")
        Listen.__init__(self)  # Note: Listen is a complex process, so for clear code, it is used independently.

        # print("Initializing Response and Speech...")  # Note: Speech is inherited by Response.
        Response.__init__(self, self.senses)
        # Note: senses are used in most of the response skills, so the Response class get it as a parameter..

        self.is_idle = True

    #     self.confidence = 0
    #
    # @property
    # def confidence(self):
    #     return self.__confidence
    #
    # @confidence.setter
    # def confidence(self, value):
    #     # 'clamping' the value between 0 and 100:
    #     self.__confidence = min(max(value, 0), 100)

    def run(self):
        """Main function for Alex to stay alive.
        It's running a loop: idle - listen(engaged) - (listen-disengaged) - idle
        When engaged, Alex take commands without requiring 'Alex' keyword
        When not engaged (some time pass without commands), 'Alex' keyword SHOULD be included in the command.
        """
        while not sig.program_terminate:
            self.is_idle = True
            wakeword_index, ringing_msg = alex.listen_for_wakeword()  # enter a loop until a wake-word is detected
            if wakeword_index == -1 and ringing_msg:
                # idle listening stopped because PDA has something to say:
                print(f"Ringing detected: {ringing_msg}")

                alex.speak(ringing_msg, about='ringing')
                # at this point the loop will continue to 'engaged' mode, waiting for user response
            else:
                timezone = self.senses.location.timezone
                return_msg = alex.wakeup_response(wakeword_index, timezone)  # generating response for the gived index
                if return_msg:
                    alex.speak(return_msg, about='wakeup')  # speak a response, and go to 'engaged' mode, see 'engage()'
                else:
                    # print('[Alex: Non-used wakeup phrase detected.]')
                    continue  # pass the lines below and goes back to idle

            self.engage()
            # after this, the while loop continue to 'idle' mode.

    def engage(self):
        """
        Main listening function to receive commands and questions.
        It uses response() from the Response class, to take care of the conversation.
        It keeps track of the conversation history and ask questions for additional data if needed.
        It has two modes:
        - Engaged: directly speak the command
        - Not Engaged: the word "Alex" need to be included in the comanad.
        """
        self.is_idle = False
        while not sig.program_terminate and not self.is_idle:
            # Enters a while loop to listen for commands. For this loop 'Alex'/'Alexandra' is required in the sentence.
            # It lasts for 1 minutes

            gibberish_talks = 0
            while not sig.program_terminate and gibberish_talks <= self.__GIBBERISH_LIMIT['engaged']:
                # Enters a loop to listen for cmd without 'Alex'. It lasts 1 minute from the last catch,
                # or if gibberish (or unused) things exceeds __GIBBERISH_LIMIT.
                # It will go here right after waking up...

                print("[Alex: Engaged. Listening...]")
                intent, slots, ringing_msg = alex.listen_for_cmd(self.__MODE_TIMEOUT['engaged'], engaged=True)

                if ringing_msg:
                    if alex.answer_expected is not None:
                        # Note: if answer is expected, the ringing message will appear and stop listening after a delay.
                        # This ringing is a reminder that an answer/confirmation is expected ('Sir are you there?).
                        alex.speak(ringing_msg, about='ringing', msg_type='ask')
                    else:
                        # The ringing is because of new reports in the queue.
                        # Terminate the ringing process and speaks all the reports...
                        # There is no 'sir are you there', because PDA is already engaged. the user should be here.
                        sig.ringing_stop()

                        # 'get_reports()' is a generator, loading the reports as a list...
                        reports = reporter.get_reports()

                        is_first = True  # used to put 'Sir/title' on front of the first message.
                        for report in reports:
                            # report[0]: element -> dict {'msg', 'about'}
                            # report[1]: elements left -> int
                            if report is not None and isinstance(report[0], dict) and isinstance(report[0]['msg'], str):
                                report_msg = f"Sir, {report[0]['msg']}" if is_first else report[0]['msg']
                                is_first = False
                                alex.speak(report_msg, about=report[0]['about'])
                else:
                    if intent and slots:

                        # 1. Processing the command and generating a response:
                        print("[Alex: processing...]")
                        if not alex.respond(intent, slots):
                            gibberish_talks += 1

                        # The loop continue to listen (engaged)

                    # if listen_for_cmd() returns None, it means its TIMEOUT passed and the engaged loop should break:
                    else:
                        # print("[Alex: Nothing understood. Disengaged...]")
                        break

            # when the 'engaged' timeout pass on silence, the PDA stops to be engaged.
            # the user needs to include 'Alex' in the command to engage the PDA again.
            gibberish_talks = 0
            if not sig.program_terminate:

                print("[Alex: Not Engaged. Listening...]")
                intent, slots, ringing_msg = alex.listen_for_cmd(self.__MODE_TIMEOUT['disengaged'], engaged=False)
                # Result is returned only if 'id'='Alex'/'Alexandra' is presented in the sentence, or there is ringing.
                # if not, after 'disengaged' timeout it breaks with 'intent' and 'slots' = None

                if ringing_msg and not alex.answer_expected:
                    # Note: usually the ringing from 'answer_expected' is caused only when PDA is already 'engaged'.
                    # So we assume the ringing is only because of new reports in the queue.

                    # terminate the ringing process and speaks all the reports:
                    reports = reporter.get_reports()

                    is_first = True  # used to put 'Sir/title' on front of the first message.
                    for report in reports:
                        # report[0]: element -> dict {'msg', 'about'}
                        # report[1]: elements left -> int
                        if report is not None and isinstance(report[0], dict) and isinstance(report[0]['msg'], str):
                            report_msg = f"Sir, {report[0]['msg']}" if is_first else report[0]['msg']
                            is_first = False
                            alex.speak(report_msg, about=report[0]['about'])

                    # Note: after all the reports are spoken, the PDA goes to 'engaged' mode.

                else:
                    if intent and slots:
                        print("[Alex: processing...]")
                        if intent == 'general':

                            if gibberish_talks <= self.__GIBBERISH_LIMIT['disengaged']:
                                gibberish_talks += 1
                            else:
                                # print("Alex: Max gibberish limit reached. Going idle...")
                                self.is_idle = True
                                break
                        else:
                            if not alex.respond(intent, slots):
                                if gibberish_talks <= self.__GIBBERISH_LIMIT['disengaged']:
                                    gibberish_talks += 1
                                else:
                                    # print("Alex: Max gibberish limit reached. Going idle...")
                                    self.is_idle = True
                                    break

                    else:
                        # print("[Alex: Nothing understood. Going idle...]")
                        self.is_idle = True
                        break  # exits the listen_for_commands loop, and it will return to idle (listen_for_wakeword).

    def clear_senses(self):
        del self.senses


# ======= MAIN ===========

print("Initializing...")

alex = AlexAPI()
"""
When instancing AlexAPI, all the threads for sensing the environment begin.
Then with calling alex.run(), the conversation loop 'idle - listen(engaged) - listen (disengaged) - idle' begins
"""

alex.speak("Initiating...")

print(f"Program started. Signal flag = {sig.program_terminate}")
alex.speak("Program started.")
alex.speak("Current location is set to")
# alex.speak("Keighley")
alex.speak(alex.senses.location.city)
time.sleep(2)

alex.run()

# alex.speak("Good morning! It's 7 AM, the weather here is 12 degrees with light rain and strong wind coming from west. The rain is expected to stop at 3pm today.", save_it=False)
# alex.speak("The next trains to Keighley are at 06:18 AM and 06:48 AM. They departure on time.", save_it=False)

time.sleep(1)
sig.program_terminate = True
print(f"Active threads running: {active_count()}")


print("Clearing the Picovoice resources...")
alex.clear_picovoice_res()
time.sleep(1)
print("Stop all threads and clearing all the res...")
# at this point we wait all the threads to finish working (because sig.program_terminate = True).
time.sleep(2)
alex.clear_senses()
print(f"Active threads left after exit: {active_count()}")

