import logging
import sys
import threading
import time
import json
import configparser

import paho.mqtt.client as mqtt

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

### Adafruit HT16K33 backpack with 1.2 inch 7x4 segment display initialization
import board
import busio
from adafruit_ht16k33 import segments

i2c = busio.I2C(board.SCL, board.SDA)
display = segments.BigSeg7x4(i2c)

class TimerDisplay:
    """
    MQTT-based timer display that listens for timer events from Home Assistant.

    Threading is used to prevent blocking the MQTT client when the timer is
    counting down.
    """

    def __init__(self, config_file='timer.ini'):
        # Load configuration
        config = configparser.ConfigParser()
        config.read(config_file)
        
        self.broker_host = config.get('MQTTSettings', 'broker_host', fallback='localhost')
        self.broker_port = config.getint('MQTTSettings', 'broker_port', fallback=1883)
        self.topic = config.get('MQTTSettings', 'topic', fallback='echopitimer/timer')
        self.username = config.get('MQTTSettings', 'username', fallback=None)
        self.password = config.get('MQTTSettings', 'password', fallback=None)
        
        self.timer_thread = None
        self.timer_active = False
        self.timer_end_time = None
        
        # Initialize MQTT client
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        
        # Set authentication if provided
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)

    def _on_connect(self, client, userdata, flags, rc):
        """Called when the client connects to the broker"""
        if rc == 0:
            logger.info(f"Connected to MQTT broker at {self.broker_host}:{self.broker_port}")
            client.subscribe(self.topic)
            logger.info(f"Subscribed to topic: {self.topic}")
        else:
            logger.error(f"Failed to connect to MQTT broker, return code {rc}")

    def _on_message(self, client, userdata, msg):
        """Called when a message is received on the subscribed topic"""
        try:
            payload = json.loads(msg.payload.decode())
            action = payload.get('action')
            
            if action == 'set':
                self._handle_set_timer(payload)
            elif action == 'update':
                self._handle_update_timer(payload)
            elif action == 'cancel':
                self._handle_cancel_timer()
            else:
                logger.warning(f"Unknown action received: {action}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON message: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def _handle_set_timer(self, payload):
        """Handle 'set' action - start a new timer"""
        end_time = payload.get('end_time')
        if not end_time:
            logger.error("Received 'set' action but no end_time provided")
            return
        
        # Check if end time has already passed
        if end_time <= time.time():
            logger.info("Received 'set' action but end_time has already passed. Ignoring")
            return
        
        # Check if another timer is already running
        if self.timer_thread is not None and self.timer_thread.is_alive():
            logger.info("Received 'set' action but another timer is already running. Ignoring")
            return
        
        # Start a new timer
        logger.info(f"Starting timer. {int(end_time - time.time())} seconds remaining")
        self.timer_end_time = end_time
        self.timer_active = True
        
        # Run timer in its own thread to prevent blocking MQTT client
        self.timer_thread = threading.Thread(target=self._run_timer)
        self.timer_thread.start()

    def _handle_update_timer(self, payload):
        """Handle 'update' action - adjust the end time of a running timer"""
        end_time = payload.get('end_time')
        if not end_time:
            logger.error("Received 'update' action but no end_time provided")
            return
        
        if self.timer_active:
            logger.info(f"Updating timer. New end time: {int(end_time - time.time())} seconds remaining")
            self.timer_end_time = end_time
        else:
            logger.info("Received 'update' action but no timer is currently active. Ignoring")

    def _handle_cancel_timer(self):
        """Handle 'cancel' action - cancel the current timer"""
        if self.timer_active:
            logger.info("Cancelling timer")
            self.timer_active = False
        else:
            logger.info("Received 'cancel' action but no timer is currently active. Ignoring")

    def _run_timer(self):
        """
        Runs a timer
        """
        display.brightness = 1.0
        start_time = time.time()
        time_remaining = self.timer_end_time - start_time
        cur_time = time_remaining

        while self.timer_active and time_remaining > 0:
            time_total = self.timer_end_time - start_time
            time_remaining = max(0, self.timer_end_time - time.time())

            # compare time on the display with time remaining, only refresh the display if a second has elapsed
            if int(cur_time) != int(time_remaining):
                self._set_time_display(int(time_remaining))
                cur_time = time_remaining

            time.sleep(0.1)

        # the timer is expired now, pulse display until timer is cancelled
        while self.timer_active:
            # fill the entire display
            display.fill(1)

            # doing some string-fu here since floats are not reliable to hold exact values
            # get current brightness and parse out decimal and mantissa
            b = float(display.brightness)
            d = int(str(b)[0])
            m = int(str(b)[2])

            # if we come in at full brightness, go down to lowest
            if int(d) == 1:
                b = 0
            else:
                # add 1 to mantissa (0.1 -> 0.2)
                m += 1

                # 0.9 -> 1.0 case
                if m == 10:
                    d = 1
                    m = 0

                b = float("{0}.{1}".format(str(d), str(m)))

            time.sleep(0.1)
            display.brightness = b

        # the timer was cancelled, clear display
        display.fill(0)

    def _set_time_display(self, seconds_remaining):
        # if time is greater than an hour, display hh:mm with blinking colon for seconds
        if seconds_remaining >= (60*60):
            hours = seconds_remaining // 3600
            minutes = (seconds_remaining - hours * 3600) // 60
            printme = "{0}{1}".format(str(hours).rjust(2, ' '), f'{minutes:02}')
            display.colon = seconds_remaining % 2 != 0
        # if the time is under an hour, display mm:ss without blinking colon
        else:
            minutes = seconds_remaining // 60
            seconds = seconds_remaining % 60
            printme = "{0}:{1}".format(f'{minutes:02}', f'{seconds:02}')

        display.print(printme)

    def run(self):
        """Connect to MQTT broker and start listening for messages"""
        try:
            logger.info(f"Connecting to MQTT broker at {self.broker_host}:{self.broker_port}")
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_forever()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            self.timer_active = False
            if self.timer_thread and self.timer_thread.is_alive():
                self.timer_thread.join(timeout=2)
            self.client.disconnect()
        except Exception as e:
            logger.error(f"Error connecting to MQTT broker: {e}")
            raise

if __name__ == '__main__':
    try:
        timer = TimerDisplay()
        timer.run()
    finally:
        logger.debug('Shutting down...')
