import time
from collections import deque


# A prototype version of PDA's Memory.
# Records all input and output conversations with the user.

class ConversationMemory:
    """A prototype version of PDA's Memory.
    It records all conversation (in/out) with the user.
    Useful when for example the user asks 'What did you said? / Could you repead'
    """

    __MEMORY_LIMIT = 10

    _requests_memory = deque(maxlen=__MEMORY_LIMIT)  # history of what user requested
    _thoughts_memory = deque(maxlen=__MEMORY_LIMIT)  # history of what PDA outputs (speaks)

    # TODO: When the class becomes more complex and require __init__(), it will switch to 'singleton design pattern'.
    # __instance = None
    #
    # def __int__(self):
    #     _requests_memory = deque(maxlen=self.__MEMORY_LIMIT)  # history of what user requested
    #     _thoughts_memory = deque(maxlen=self.__MEMORY_LIMIT)  # history of what PDA outputs
    #
    # # The below will ensure that only one instance of the class will be created
    # # Needed because we can use the class both in Speech and Response, calling 'memory = ConversationMemory()
    # def __new__(cls):
    #     if cls.__instance is None:
    #         cls.__instance = super().__new__(cls)
    #     return cls.__instance

    @classmethod
    def get_last_request(cls) -> dict:
        if len(cls._requests_memory) > 0:
            return cls._requests_memory[-1]
        else:
            return None

    @classmethod
    def get_last_thought(cls) -> dict:
        if len(cls._thoughts_memory) > 0:
            return cls._thoughts_memory[-1]
        else:
            return None

    @classmethod
    def add_request(cls, intent, slots, status='completed', note=""):
        if intent and slots:  # check if the line is empty or None
            timestamp = int(time.time())
            request_to_add = {'timestamp': timestamp, 'intent': intent, 'slots': slots, 'status': status, 'note': note}
            # 'failed' means that the PDA give up of succeeding the command because some reason.
            # 'It is useful if later the user ask 'Try again'
            cls._requests_memory.append(request_to_add)
            # print(f"Appended to memory: {request_to_add}")
            # Note: as a deque, if the elements exceed the limit (cls.__MEMORY_LIMIT), it will delete the oldest ones.

    @classmethod
    def add_thought(cls, spoken_msg: str, about: str, msg_type: str):
        """Note: 'about' is a short explanation of the spoken sentence, used to answer a question 'what did you said?'
            -'What did you say?' -'I just gave you an answer about {about} Sir.' / -'I just asked you about {about}
            For the question 'could you repeat' the 'last_thought['msg']=spoken_msg' is used.

        """
        if about and spoken_msg:
            timestamp = int(time.time())
            # currently not used:
            # # if spoken_msg is a long answer (for example weather forecast), it will just save a 'sample explanation'
            # if len(spoken_msg) > 50:
            #     msg_to_add = 'detailed answer' # USER: 'what?' PDA: 'I said {spoken_msg} about {about}.'
            # else:
            #     msg_to_add = spoken_msg
            # user: 'Could you repeat?' | PDA: 'Sure. {spoken_msg}'
            # but if the request is 'What did you said?', PDA will answer 'I just gave you an answer about {about} Sir.'

            # Note: if there are several sentences spoken from one response, they are all appended to the same memory.
            last_thought = cls.get_last_thought()
            if last_thought and (timestamp - last_thought['timestamp'] < 5) and last_thought['about'] == about:
                # appending the spoken message to the last thought message and updating the timestamp
                last_thought['msg'] += f" {spoken_msg}"
                last_thought['timestamp'] = timestamp
                # print(f"Thought updated to {last_thought}")
            else:
                thought_to_add = {'timestamp': timestamp, 'about': about, 'type': msg_type, 'msg': spoken_msg}
                cls._thoughts_memory.append(thought_to_add)
                # print(f"Appended to memory: {thought_to_add}")
