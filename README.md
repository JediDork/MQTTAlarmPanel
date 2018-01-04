# MQTT Alarm Panel using Kivy
MQTT Alarm Panel is a UI built using Kivy for the Raspberry Pi. While the application can be modified to suit any kivy-capable hardware, its main purpose is to avoid using X and therefore save on limited Raspberry Pi resources. 

# Features
1. Runs on Kivy/Python - No need to boot to Raspberry Pi desktop!
2. Control of Manual MQTT Alarm in Home Assistant thanks to paho-mqtt
3. GPIO control for a Piezo Buzzer
4. Screensaver for night mode
5. Settings menu (currently in development - half way there)

# Usage
The settings are currently hard-coded. After you have cloned the repo, edit main.py and change lines 22-48 as required.

Notes:
Some modules may need to be installed prior. Ensure you have the following modules:
- sudo pip install RPi.GPIO
- sudo pip install rpi_backlight

Obviously Kivy and Python needs to be installed too - see https://kivy.org/docs/installation/installation-rpi.html

You can change App background simply by changing bg.jpg to an image of your choosing

# Currently in Development
1. Settings menu to save config and avoid hard-coding.
2. MQTT settings to include username/password.