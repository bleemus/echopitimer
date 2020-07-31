# echopitimer
Raspberry Pi Timer implementation for 7-segment display

# Motivation
While I enjoy the simplicity of spoken word commands available on Alexa, I find myself annoyed when having to consistently asking for status updates.

This is the most prevalent when using timers in the kitchen, which our family uses multiple times daily.  While getting status updates via voice, I often had to repeat what I was saying or wait for a quiet moment in the house to get my command in.  I wanted a way to use the Echo to set a timer easily without having to stop what I'm cooking, but craved an easy to read display to show these timers.

While I know that there are Echo devices with screens, I didn't need any of the other functionality, and thought it a good opportunity to tinker with hardware to come up with a custom solution.

# Hardware used
1. [Raspberry Pi Zero W with installed headers](https://www.raspberrypi.org/pi-zero-w/)
1. [Adafruit 1.2" 4-Digit 7-Segment Display w/I2C Backpack](https://www.adafruit.com/product/1270)
1. [T expansion board for prototyping](https://www.adafruit.com/product/2028)
1. [Echo dot or whatever flavor](https://www.amazon.com/echo)

# Installation/configuration
## raspbian install
* https://learn.adafruit.com/raspberry-pi-zero-creation/install-os-on-to-sd-card

### enable ssh and wifi
* https://learn.adafruit.com/raspberry-pi-zero-creation/text-file-editing

## wiring
* https://learn.adafruit.com/adafruit-led-backpack/python-wiring-and-setup-d74df15e-c55c-487a-acce-a905497ef9db

## configuration of i2c interface via circuitpi
* https://learn.adafruit.com/circuitpython-on-raspberrypi-linux/installing-circuitpython-on-raspberry-pi

## configuration of alexa gadget
* https://github.com/alexa/Alexa-Gadgets-Raspberry-Pi-Samples#prerequisites

## coding
Details coming soon!
