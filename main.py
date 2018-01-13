import kivy
kivy.require("1.9.0")

import sys
import time
import random
import yaml
import io
import urllib
import os.path
import os
import datetime
import threading
from kivy.app import App
from kivy.config import Config
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.properties import StringProperty
from kivy.core.image import Image as CoreImage
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.uix.label import Label
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt
from collections import deque

# Settings file now implemented. Refer to settings.yaml and try to avoid changing the code below
# TODO: Hard-code appSetting variables directly to the command, instead of referring through a 3rd variable
cwd = os.path.dirname(os.path.abspath(__file__))
with open(cwd + "/settings.yaml", 'r') as ymlfile:
    appSettings = yaml.load(ymlfile)

# Screen setup. Official RPi touch screen is 800(x) x 480(y)
screen_res_x = appSettings['screen']['x']
screen_res_y = appSettings['screen']['y']

# Alarm Setup. 0-9. Can be any length!
alarmCode = appSettings['alarm']['code']

# MQTT setup
broker_address = appSettings['mqtt']['broker']
broker_port = appSettings['mqtt']['port']
broker_clientid = str(random.randint(1000,10000))
broker_statetopic = appSettings['mqtt']['state_topic']
broker_comtopic = appSettings['mqtt']['com_topic']
broker_lastmsg = ""

# GPIO setup. Use BCM pin numbering (i.e GPIO18 = 18)
buzzerPin = appSettings['piezo']['pin']

# Text updates for UI and Backend. Change if you want.
sentText = appSettings['mqtt']['sent']
failText = appSettings['mqtt']['fail']
gpio_warning = appSettings['warnings']['gpio']
bl_warning = appSettings['warnings']['backlight']

# Raspberry Pi Backlight control. Goes dim after a set time, then returns after a set time
# dimmer_night: Screen will dim after this time. Format is hour, minutes, seconds
dimmer_night = datetime.time(appSettings['dimmer']['night_hour'], appSettings['dimmer']['night_min'], appSettings['dimmer']['night_sec'])
dimmer_day = datetime.time(appSettings['dimmer']['day_hour'], appSettings['dimmer']['day_min'], appSettings['dimmer']['day_sec'])

# Leave these values alone!
dimmer_night = dimmer_night.strftime("%H:%M:%S")
dimmer_day = dimmer_day.strftime("%H:%M:%S")

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(buzzerPin, GPIO.OUT)
    GPIO.output(buzzerPin, 0)
except Exception as e:
    print("Error importing RPi.GPIO. try SUDO or make sure RPi.GPIO module is installed.")
    print(e)

try:
    import rpi_backlight as bl
    bl.set_brightness(appSettings['dimmer']['day_value'])
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
            bl.set_brightness(appSettings['dimmer']['night_value'], smooth=True, duration=10)
        except Exception:
            print(bl_warning)
    else:
        print("[INFO   ] Day Mode Active")
        try:
            bl.set_brightness(appSettings['dimmer']['day_value'], smooth=True, duration=10)
        except Exception:
            print(bl_warning)

def on_message(client, userdata, message):
    try:
        print("[INFO   ] MQTT Message: " ,str(message.payload.decode("utf-8")))
        msgPreformat = str(message.payload.decode("utf-8")) 
        msgFormatted = str.replace(msgPreformat,"_"," ").upper()
        App.get_running_app().root.ids.status.text = msgFormatted
        broker_lastmsg = msgFormatted
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



class RestartPopup(Popup):
    def doRestart(self):
        os.system("sudo shutdown -r 1")
        print("Rebooting in 60 seconds...")
        try:
            p = psutil.Process(os.getpid())
            for handler in p.get_open_files() + p.connections():
                os.close(handler.fd)
        except Exception as e:
            print ("[WARNING] ", e)

        python = sys.executable
        os.execl(python, python, *sys.argv)

class MenuPopup(Popup):
    def changeSlider(self, value):
        global bl_warning
        print (int(value))
        try:    
            bl.set_brightness(int(value))
        except Exception:
            print (bl_warning)

    def checkLeftBtn(self, labelText):
        appSettings['mqtt']['broker'] = str(self.ids.mqtt_host.text)
        appSettings['mqtt']['port'] = int(self.ids.mqtt_port.text)
        appSettings['mqtt']['username'] = str(self.ids.mqtt_username.text)
        appSettings['mqtt']['pass'] = str(self.ids.mqtt_pass.text)
        appSettings['mqtt']['state_topic'] = str(self.ids.mqtt_state.text)
        appSettings['mqtt']['com_topic'] = str(self.ids.mqtt_com.text)
        appSettings['piezo']['pin'] = int(self.ids.buzzer_pin.text)
        appSettings['alarm']['code'] = str(self.ids.alarm_code.text)
        appSettings['screen']['x'] = str(self.ids.screen_x.text)
        appSettings['screen']['y'] = str(self.ids.screen_y.text)
        appSettings['dimmer']['night_hour'] = int(self.ids.night_hour.text)
        appSettings['dimmer']['night_min'] = int(self.ids.night_min.text)
        appSettings['dimmer']['night_sec'] = int(self.ids.night_sec.text)
        appSettings['dimmer']['day_hour'] = int(self.ids.day_hour.text)
        appSettings['dimmer']['day_min'] = int(self.ids.day_min.text) 
        appSettings['dimmer']['day_sec'] = int(self.ids.day_sec.text)
        appSettings['dimmer']['night_value'] = int(self.ids.night_value.value)
        appSettings['dimmer']['day_value'] = int(self.ids.day_value.value)
        cwd = os.path.dirname(os.path.abspath(__file__))
        with open(cwd + '/settings.yaml', 'w') as outfile:
            yaml.dump(appSettings, outfile, default_flow_style=False)
        popup2 = RestartPopup()
        popup2.open()
        self.dismiss()

class MjpegViewer(Image):

    url = StringProperty()

    def start(self):
        self.quit = False
        self._queue = deque()
        self._thread = threading.Thread(target=self.read_stream)
        self._thread.daemon = True
        self._thread.start()
        self._image_lock = threading.Lock()
        self._image_buffer = None
        Clock.schedule_interval(self.update_image, 1 / 30.)

    def stop(self):
        self.quit = True
        self._thread.join()
        Clock.unschedule(self.read_queue)

    def read_stream(self):
        stream = urllib.urlopen(self.url)
        bytes = ''
        while not self.quit:
            bytes += stream.read(1024)
            a = bytes.find('\xff\xd8')
            b = bytes.find('\xff\xd9')
            if a != -1 and b != -1:
                jpg = bytes[a:b + 2]
                bytes = bytes[b + 2:]

                data = io.BytesIO(jpg)
                im = CoreImage(data,
                               ext="jpeg",
                               nocache=True)
                with self._image_lock:
                    self._image_buffer = im

    def update_image(self, *args):
        im = None
        with self._image_lock:
            im = self._image_buffer
            self._image_buffer = None
        if im is not None:
            self.texture = im.texture
            self.texture_size = im.texture.size

def Screensaver(Popup):
    pass

class AlarmGridLayout(GridLayout):
    def checkCode(self, code, mode):
        global broker_lastmsg
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
        global appSettings
        if code:
            if (self.display.text == alarmCode):
                if (mode == "ARM_AWAY"):
                    client.publish(broker_comtopic,mode)
                    App.get_running_app().root.ids.status.text = sentText
                if (mode == "ARM_HOME"):
                    client.publish(broker_comtopic,mode)
                    App.get_running_app().root.ids.status.text = sentText
                if (mode == "SCREENSAVER"):
                    cam1 = MjpegViewer(url="http://10.1.1.75/cgi-bin/nph-zms?mode=jpeg&scale=100&maxfps=5&buffer=1000&monitor=1&user=cam&pass=cam")
                    cam1.start()
                    buildWidget = GridLayout()
                    buildWidget.cols = 2
                    buildWidget.add_widget(cam1)

                    popup = Popup(title='Camera View',content=buildWidget,size_hint=(0.9, 0.9),auto_dismiss=True)
                    popup.open()
                if (mode == "DISARM"):
                    client.publish(broker_comtopic,mode)
                    App.get_running_app().root.ids.status.text = sentText
                if (mode == "SETTINGS"):
                    # Display settings screen
                    popup = MenuPopup()
                    popup.ids.mqtt_host.text = appSettings['mqtt']['broker']
                    popup.ids.mqtt_port.text = str(appSettings['mqtt']['port'])
                    popup.ids.mqtt_username.text = appSettings['mqtt']['username']
                    popup.ids.mqtt_pass.text = appSettings['mqtt']['pass']
                    popup.ids.mqtt_state.text = appSettings['mqtt']['state_topic']
                    popup.ids.mqtt_com.text = appSettings['mqtt']['com_topic']
                    popup.ids.buzzer_pin.text = str(appSettings['piezo']['pin'])
                    popup.ids.alarm_code.text = appSettings['alarm']['code']
                    popup.ids.screen_x.text = appSettings['screen']['x']
                    popup.ids.screen_y.text = appSettings['screen']['y']
                    popup.ids.night_hour.text = str(appSettings['dimmer']['night_hour'])
                    popup.ids.night_min.text = str(appSettings['dimmer']['night_min'])
                    popup.ids.night_sec.text = str(appSettings['dimmer']['night_sec'])
                    popup.ids.day_hour.text = str(appSettings['dimmer']['day_hour'])
                    popup.ids.day_min.text = str(appSettings['dimmer']['day_min'])
                    popup.ids.day_sec.text = str(appSettings['dimmer']['day_sec'])
                    popup.ids.night_value.value = appSettings['dimmer']['night_value']
                    popup.ids.day_value.value = appSettings['dimmer']['day_value']
                    popup.open()

            App.get_running_app().root.ids.entry.text = ""
            try:
                piezoBeep = threading.Thread(makeBeep(0.8))
                piezoBeep.start()
            except Exception:
                print (gpio_warning)

    def processBtn(self, btn):
        global gpio_warning
        self.display.text += btn
        try:
            piezoBeep = threading.Thread(makeBeep(0.2))
            piezoBeep.start()
        except Exception:
            print (gpio_warning)

class MQTTPanelApp(App):
    def build(self):
        return AlarmGridLayout()

    def on_start(self, **kwargs):
        global broker_lastmsg
        if (broker_lastmsg == ""):
            App.get_running_app().root.ids.status.text = "ARM/DISARM TO BEGIN"
        else:
            App.get_running_app().root.ids.status.text = broker_lastmsg

MQTTApp = MQTTPanelApp()
MQTTApp.run()
try:
    GPIO.cleanup()
except Exception:
    print("Error cleaning up, but continuing on....")
