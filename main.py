import kivy
kivy.require("1.9.0")

import sys
import time
import random
import json
import os.path
import datetime
import threading
from kivy.app import App
from kivy.config import Config
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.uix.label import Label
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt

# Screen setup. Official RPi touch screen is 800(x) x 480(y)
screen_res_x = "800"
screen_res_y = "480"

# Alarm Setup. 0-9. Can be any length!
alarmCode = "1230"

# MQTT setup
broker_address = "10.1.1.75"
broker_port = 1883
broker_clientid = str(random.randint(1000,10000))
broker_statetopic = "home/alarm"
broker_comtopic = "home/alarm/set"

# GPIO setup. Use BCM pin numbering (i.e GPIO18 = 18)
buzzerPin = 18

# Text updates for UI and Backend. Change if you want.
sentText = "Update Sent"
failText = "Update Failed"
gpio_warning = "[WARNING] GPIO not connected"
bl_warning = "[WARNING] BACKLIGHT not connected"

# Raspberry Pi Backlight control. Goes dim after a set time, then returns after a set time
# dimmer_night: Screen will dim after this time. Format is hour, minutes, seconds
dimmer_night = datetime.time(22, 00, 00)
dimmer_day = datetime.time(6, 30, 00)

# Leave these values alone!
dimmer_night = dimmer_night.strftime("%H:%M:%S")
dimmer_day = dimmer_day.strftime("%H:%M:%S")

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(buzzerPin, GPIO.OUT)
    GPIO.output(buzzerPin, 0)
except Exception:
    print("Error importing RPi.GPIO. try SUDO or make sure RPi.GPIO module is installed.")

try:
    import rpi_backlight as bl
except Exception:
    print("Error starting backlight. Try SUDO or make sure rpi_backlight module is installed.")

# Set graphic display
Config.set('graphics', 'width', screen_res_x)
Config.set('graphics', 'height', screen_res_y)

# Threaded Piezo loop to avoid stalling the GUI when buttons are pressed
def makeBeep(length):
    global buzzerPin
    if (length == 0):
        try:
            GPIO.output(buzzerPin, 0)
        except Exception:
            print (gpio_warning)
    else:
        try:
            GPIO.output(buzzerPin, 1)
            time.sleep(length)
            GPIO.output(buzzerPin, 0)
        except Exception:
            print (gpio_warning)

# Progress bar callback for when "PENDING" is displayed 
def progBar(dt):
    global buzzerPin
    global gpio_warning
    if (App.get_running_app().root.ids.bar.value == App.get_running_app().root.ids.bar.max):
        App.get_running_app().root.ids.bar.value = 0
        try:
            GPIO.output(buzzerPin, 0)
        except Exception:
            print (gpio_warning)
        return False
    elif (App.get_running_app().root.ids.status.text != "PENDING") & (App.get_running_app().root.ids.status.text != "TRIGGERED"):
        App.get_running_app().root.ids.bar.value = 0
        try:
            GPIO.output(buzzerPin, 0)
        except Exception:
            print (gpio_warning)
        return False
    else:
        App.get_running_app().root.ids.bar.value = App.get_running_app().root.ids.bar.value + 0.5
        try:
            GPIO.output(buzzerPin, 1)
        except Exception:
            print (gpio_warning)

def dimmer_checker(dt):
    global dimmer_day
    global dimmer_night
    global bl_warning
    curtime = datetime.datetime.now()
    curtime = curtime.strftime("%H:%M:%S")

    if ((curtime > dimmer_night) & (curtime > dimmer_day)) | ((curtime < dimmer_night) & (curtime < dimmer_day)):
        print("[INFO   ] Night Mode Active")
        try:
            bl.set_brightness(20, smooth=True, duration=10)
        except Exception:
            print(bl_warning)
    else:
        print("[INFO   ] Day Mode Active")
        try:
            bl.set_brightness(255, smooth=True, duration=10)
        except Exception:
            print(bl_warning)

def on_message(client, userdata, message):
    try:
        print("[INFO   ] MQTT Message: " ,str(message.payload.decode("utf-8")))
        msgPreformat = str(message.payload.decode("utf-8")) 
        msgFormatted = str.replace(msgPreformat,"_"," ").upper()
        App.get_running_app().root.ids.status.text = msgFormatted
        if (msgFormatted == "PENDING"):
            App.get_running_app().root.ids.bar.value = 0
            App.get_running_app().root.ids.bar.max = 60
            doProg = Clock.schedule_interval(progBar, 0.5)
    except Exception as e: print(e)

client = mqtt.Client(broker_clientid) #create new instance
client.connect(broker_address,broker_port) #connect to broker
client.on_message=on_message
client.subscribe(broker_statetopic)
client.loop_start()
doDimmer = Clock.schedule_interval(dimmer_checker, 60)

#from kivy.animation import Animation
#from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelHeader
#from kivy.uix.switch import Switch
#from kivy.uix.widget import Widget
#from kivy.uix.button import Button
#from kivy.uix.togglebutton import ToggleButton
#from kivy.uix.image import Image
#from kivy.uix.textinput import TextInput
#from kivy.clock import Clock
#from kivy.factory import Factory
#from kivy.lang import Builder

class MenuPopup(Popup):
    def changeSlider(self, value):
        global bl_warning
        print (int(value))
        try:    
            bl.set_brightness(int(value))
        except Exception:
            print (bl_warning)

class AlarmGridLayout(GridLayout):
    def checkCode(self, code, mode):
        global broker_address
        global broker_port
        global broker_statetopic
        global broker_comtopic
        global buzzerPin
        global screen_res_x
        global screen_res_y
        global gpio_warning
        global sentText
        global failText
        global alarmCode
        if code:
            if (self.display.text == alarmCode):
                if (mode == "ARM_AWAY"):
                    client.publish(broker_comtopic,mode)
                    App.get_running_app().root.ids.status.text = sentText
                else:
                    App.get_running_app().root.ids.status.text = failText
                if (mode == "ARM_HOME"):
                    client.publish(broker_comtopic,mode)
                    App.get_running_app().root.ids.status.text = sentText
                else:
                    App.get_running_app().root.ids.status.text = failText
                if (mode == "ARM_NIGHT"):
                    client.publish(broker_comtopic,mode)
                    App.get_running_app().root.ids.status.text = sentText
                else:
                    App.get_running_app().root.ids.status.text = failText
                if (mode == "DISARM"):
                    client.publish(broker_comtopic,mode)
                    App.get_running_app().root.ids.status.text = sentText
                else:
                    App.get_running_app().root.ids.status.text = failText
                if (mode == "SETTINGS"):
                    # Display settings screen
                    popup = MenuPopup()
                    popup.ids.mqtt_host.text = broker_address
                    popup.ids.mqtt_port.text = str(broker_port)
                    popup.ids.mqtt_state.text = broker_statetopic
                    popup.ids.mqtt_com.text = broker_comtopic
                    popup.ids.buzzer_pin.text = str(buzzerPin)
                    popup.ids.alarm_code.text = alarmCode
                    popup.ids.screen_x.text = screen_res_x
                    popup.ids.screen_y.text = screen_res_y
                    popup.open()
                else:
                    App.get_running_app().root.ids.status.text = failText

            App.get_running_app().root.ids.entry.text = ""
            try:
                piezoBeep = threading.Thread(makeBeep, 0.8)
                piezoBeep.start()
            except Exception:
                print (gpio_warning)

    def processBtn(self, btn):
        global gpio_warning
        self.display.text += btn
        try:
            piezoBeep = threading.Thread(makeBeep, 0.2)
            piezoBeep.start()
        except Exception:
            print (gpio_warning)

class MQTTPanelApp(App):
    def build(self):
        return AlarmGridLayout()

MQTTApp = MQTTPanelApp()
MQTTApp.run()
try:
    GPIO.cleanup()
except Exception:
    print("Error cleaning up, but continuing on....")
