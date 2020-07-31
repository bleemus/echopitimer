#
# Copyright 2019 Amazon.com, Inc. or its affiliates.  All Rights Reserved.
# These materials are licensed under the Amazon Software License in connection with the Alexa Gadgets Program.
# The Agreement is available at https://aws.amazon.com/asl/.
# See the Agreement for the specific terms and conditions of the Agreement.
# Capitalized terms not defined in this file have the meanings given to them in the Agreement.
#

import logging
import sys
import threading
import time
import dateutil.parser

from agt import AlexaGadget

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

### Adafruit HT16K33 backpack with 1.2 inch 7x4 segment display initialization
import board
import busio
from adafruit_ht16k33 import segments

i2c = busio.I2C(board.SCL, board.SDA)
display = segments.BigSeg7x4(i2c)

class TimerGadget(AlexaGadget):
    """
    An Alexa Gadget that reacts to a single timer set on an Echo device.

    Threading is used to prevent blocking the main thread when the timer is
    counting down.
    """

    def __init__(self):
        super().__init__()
        self.timer_thread = None
        self.timer_token = None
        self.timer_end_time = None

    def on_alerts_setalert(self, directive):
        """
        Handles Alerts.SetAlert directive sent from Echo Device
        """
        # check that this is a timer. if it is something else (alarm, reminder), just ignore
        if directive.payload.type != 'TIMER':
            logger.info("Received SetAlert directive but type != TIMER. Ignorning")
            return

        # parse the scheduledTime in the directive. if is already expired, ignore
        t = dateutil.parser.parse(directive.payload.scheduledTime).timestamp()
        if t <= 0:
            logger.info("Received SetAlert directive but scheduledTime has already passed. Ignoring")
            return

        # check if this is an update to an alrady running timer (e.g. users asks alexa to add 30s)
        # if it is, just adjust the end time
        if self.timer_token == directive.payload.token:
            logger.info("Received SetAlert directive to update to currently running timer. Adjusting")
            self.timer_end_time = t
            return

        # check if another timer is already running. if it is, just ignore this one
        if self.timer_thread is not None and self.timer_thread.isAlive():
            logger.info("Received SetAlert directive but another timer is already running. Ignoring")
            return

        # start a thread to update the display
        logger.info("Received SetAlert directive. Starting a timer. " + str(int(t - time.time())) + " seconds left..")
        self.timer_end_time = t
        self.timer_token = directive.payload.token

        # run timer in it's own thread to prevent blocking future directives during count down
        self.timer_thread = threading.Thread(target=self._run_timer)
        self.timer_thread.start()

    def on_alerts_deletealert(self, directive):
        """
        Handles Alerts.DeleteAlert directive sent from Echo Device
        """
        # check if this is for the currently running timer. if not, just ignore
        if self.timer_token != directive.payload.token:
            logger.info("Received DeleteAlert directive but not for the currently active timer. Ignoring")
            return

        # delete the timer, and stop the currently running timer thread
        logger.info("Received DeleteAlert directive. Cancelling the timer")
        self.timer_token = None

    def _run_timer(self):
        """
        Runs a timer
        """
        display.brightness = 1.0
        start_time = time.time()
        time_remaining = self.timer_end_time - start_time
        cur_time = time_remaining

        while self.timer_token and time_remaining > 0:
            time_total = self.timer_end_time - start_time
            time_remaining = max(0, self.timer_end_time - time.time())

            # compare time on the display with time remaining, only refresh the display if a second has elapsed
            if int(cur_time) != int(time_remaining):
                self._set_time_display(int(time_remaining))
                cur_time = time_remaining

            time.sleep(0.1)

        # the timer is expired now, pulse display until timer is cancelled
        while self.timer_token:
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

if __name__ == '__main__':
    try:
        TimerGadget().main()
    finally:
        logger.debug('Shutting down...')
