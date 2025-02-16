# Alex-PDA
----------
Welcome to my Personal Digital Assistant project, built with offline mode in mind.

Still uses the Google TTS (Text To Speech) API for the voice generation, **but it records the short and most used phrases**, so they will be available offline, when needed again.
For Speech Recognition, I am working on two versions: 
1. Using the API's called "Rhino" / "Cheetah" (for speech-to-text decode), and "Porcupine" (for wake-word detection), from [picovoice.ai](https://picovoice.ai/)
2. Using the OpenAi Whisper (still working on this, before a stable version to be uploaded here). 

**The PDA is able to handle events and sensor-data on a background.** It is ment to work with MQTT communication protocol (over wifi) for Smart-home devices. It also has functions to work with data from LoRa radio (via serial), so it can get data from distant devices.

*Tested on Raspberry Pi 4 and Khadas Edge2 boards, but the version with 'picovoice' speech-to-text should work on Raspberry Pi zero 2W and Pi 3+.*


* For Ubuntu install instructions on raspberry pi / Khadas, look the file INSTALL_INSTRUCTIONS.txt
* Ensure you have your gtts_accnt.json google application credentials file placed in your main folder

-- For application notes, look the file "Application_Notes.rtf"

