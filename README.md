# MQTT Alarm Panel using Kivy
MQTT Alarm Panel is a UI built using Kivy for the Raspberry Pi. While the application can be modified to suit any kivy-capable hardware, its main purpose is to avoid using X and therefore save on limited Raspberry Pi resources. 

# Features
1. Runs on Kivy/Python - No need to boot to Raspberry Pi desktop!
2. Control of Manual MQTT Alarm in Home Assistant thanks to paho-mqtt
3. GPIO control for a Piezo Buzzer thanks to RPi.GPIO
4. Screen dimmer for night mode thanks to rpi_backlight
5. Settings menu (currently in development - half way there)

# Usage
The settings are currently hard-coded. After you have cloned the repo, edit main.py and change lines 22-48 as required.

Notes:
Some modules may need to be installed prior. Ensure you have the following modules:
- sudo pip install RPi.GPIO
- sudo pip install rpi_backlight
- sudo pip install paho-mqtt

Obviously Kivy and Python need to be installed too - see https://kivy.org/docs/installation/installation-rpi.html

The seetinigs menu can be reached by typing your alarm code + * on the interface. As mentioned it is not complete but will be soon!

# Currently in Development
1. Settings menu to save config and avoid hard-coding.
2. Add MQTT username/password to connection string (and add to settings menu).
4. Add Night/Day to settings menu
5. Bug fix: Check for network connection prior to attempting connection to MQTT service
6. Add PIR service to indicate where sensors are being triggered
7. Start a screensaver after a while