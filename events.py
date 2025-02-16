"""
This module has a custom written 'signal' parameters,
used in all the files and classes to communicate with each other.
The main reason of creating it, is to tell all the 'on-running' loops and THREADS,
that an event has occurred, for example 'The program is exiting. Terminate all threads'.
"""
import random
import time
from typing import List

import threading


class Signals:
    program_terminate = False  # signal for program termination. It stops all the running threads.

    """ WORKING ON RINGING SIGNAL ===
    1. If a function running on a background needs an attention, it will engage sig.ringing_start().
    - This will call the user and wait for his response.
    - if user does not answer, the message will be saved in a queue, waiting the user to appear.
    2. If the respond() rings for attention, it means the user engaged the PDA, but the respond() needs more data.
    - this will cause ringing for several times, and if user does not answer, the operation will be cancelled.
    3. If PDA is sleeping and a function has a report to tell, it is the 'ringing' used.
    - If PDA does not sleep, there is no ringing. the reporter directly says the report.

    '_ringing_msg' is used to store the ringing message (as "Sir are you there?")
    and also to stop the LISTENING thread, in order the message to be spoken.
    - 'if _ringing_msg is not None', it is a signal to break the LISTEN functions and speak the message, and clear it.
    - When the message queue is cleared, this will allow LISTENING to continue, in order the user to answer the call.
    - However, while 'is_ringing' is True, the ringing thread will periodically inject a new _ringing_msg,
    reminding the user that the system needs its attention.
    """
    _ringing_msg = None
    # ringing_msg is a simple string for engaging the user 'Sir are you there?'

    is_ringing = False
    __thread = None

    @classmethod
    def set_ringing_msg(cls, msg: str):
        if msg:
            cls._ringing_msg = msg

    @classmethod
    def get_ringing_msg(cls):
        # Note: every time the ringing_msg is read, it is cleared.
        if cls._ringing_msg is not None:
            msg = cls._ringing_msg
            cls._ringing_msg = None
            return msg
        else:
            return None

    @classmethod
    def clear_ringing_msg(cls):
        if cls._ringing_msg is not None:
            cls._ringing_msg = None

    @classmethod
    def __ringing_thread(cls, mode: str):
        # if mode == 'answer-expected': it waits a time, then injects message, then waits a time...
        # if mode == 'new-report' it inject a message, then waits, then inject the message, then waits...

        # Note: The attempt counts are emilated by the length of the 'ringing-msg' list. Every call is 1 sec.

        mode_sequence = {
            'new-report': {
                'sequence': ['wait', 'ring', 'wait', 'ring', 'wait', 'final', 'wait', 'end'],
                'ringing-msg': ["Sir?", "Sir are you there?", "Sir!"],
                'final-call': "Anyone?",
                'end-msg': None
            },
            'answer-expected': {
                'sequence': ['ring', 'wait', 'ring', 'wait', 'final', 'wait', 'end'],
                'ringing-msg': ["Sir?", "Sir I need your answer.", "Sir!"],
                'final-call': "I'm about to cancel your request.",
                'end-msg': ["Ok whatever.", "Ok never mind."]
            }
        }

        cls.is_ringing = True
        # print(f"Ringing started. Mode={mode}...")

        if mode == 'answer-expected':
            ringing_sequence = mode_sequence[mode]
        else:
            ringing_sequence = mode_sequence['new-report']

        for cmd in ringing_sequence['sequence']:
            # calling the user 3 times
            for time_tick in range(5):
                # calling every 5 seconds.
                # But if there is a termination signal detected, the ringing stops.
                if time_tick == 0:
                    if cmd == 'wait':
                        pass
                    elif cmd == 'ring':
                        chs_index = random.randrange(len(ringing_sequence['ringing-msg'])-1)
                        ring_msg = ringing_sequence['ringing-msg'].pop(chs_index)
                        cls.set_ringing_msg(ring_msg)
                    elif cmd == 'final':
                        ring_msg = ringing_sequence['final-call']
                        cls.set_ringing_msg(ring_msg)
                    elif cmd == 'end':
                        if ringing_sequence['end-msg']:
                            ring_msg = random.choice(ringing_sequence['end-msg'])
                            cls.set_ringing_msg(ring_msg)
                            cls.is_ringing = False

                if not cls.is_ringing or cls.program_terminate:
                    break
                else:
                    time.sleep(1)

        if cls.program_terminate:
            print("RINGING thread stopped successfully.")

    @classmethod
    def ringing_start(cls, mode: str):
        # mode: 'answer_expected' / 'new_report'
        # starting the thread
        if not cls.is_ringing:
            # print("Start ringing...")
            cls.__thread = threading.Thread(target=cls.__ringing_thread, args=(mode,))
            cls.__thread.start()
        else:
            print(f"WARN: Something tried to start ringing on mode: {mode}, but it is already started.")

    @classmethod
    def ringing_stop(cls):
        cls.is_ringing = False
        cls.clear_ringing_msg()
        if cls.__thread is not None and cls.__thread.is_alive():
            print("The RINGING thread is running. Stopping it...")
            cls.__thread.join()
            print("RINGING thread stopped successfully.")

    @classmethod
    def ringing_restart(cls):
        ...


"""
Reporter queue is used from Respond class. 
Every function can add its report to the queue at any time.
It is important, when a function add new report. to use the SIGNAL class to ring to the user.
When the user answer, the RESPOND class will take care for respond every report in the queue to the user.
"""


class EventReporter:
    """
    Class, used to handle event messages from all processes,
    and then inject this messages in the main program, to be spoken.
    It is able to STOP the listening process, in order to speak the incoming message.
    """

    _reporter_queue: List[dict] = []

    is_reports = False

    @classmethod
    def add_to_queue(cls, msg, msg_about='report'):
        # TODO: add a protection if two methods try to update the queue at the same time...
        try:
            report_element = {'msg': msg, 'about': msg_about}
            cls._reporter_queue.append(report_element)
            # TODO: when we add to queue, the RINGING should be started from the function who added the report!!!

            print(f"A report is added: {msg}, {msg_about}.")
        except Exception as e:
            print(e)

    @classmethod
    def clear_queue(cls):
        try:
            cls._reporter_queue.clear()
            print("The Reporter Queue cleared successfully")
        except Exception as e:
            print(e)
            return False
        return True

    @classmethod
    def get_next_report(cls):
        # TODO: Same protection as above, here
        try:
            if cls._reporter_queue:
                element = cls._reporter_queue.pop()
                print(f"Next to report: {element}")
                elements_left = len(cls._reporter_queue)
                return element, elements_left
            else:
                return None
        except Exception as e:
            print(e)
            return None

    # a generator version of get_nex_report() method...
    @classmethod
    def get_reports(cls):
        while len(cls._reporter_queue) > 0:
            try:
                report = cls._reporter_queue.pop()
                print(f"Next to report: {report}")
                yield report
            except Exception as e:
                print(e)
                yield None



# def my_generator():
#     for i in range(5):
#         yield f"message {i}"
#
# # loop over the values returned by the generator
# for message in my_generator():
#     print(message)


# def my_generator():
#     message_list = []
#     for i in range(5):
#         message_list.append(f"message {i}")
#
#     while len(message_list) > 0:
#         message = message_list.pop()  # last in - first out.
#         yield message
#
#
# # loop over the values returned by the generator
# for my_message in my_generator():
#     print(my_message)
#
# generator = my_generator()
# for my_message in generator:
#     print(my_message)