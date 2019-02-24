# Domoticz Plugin example for Serial units with M-Bus (meter-bus) interface.

A hardware interface is needed.
DIY TTL * https://openenergymonitor.org/forum-archive/node/1944.html
DIY RS-232
DIY Sniffer 
Or Commercial

## Compability
Developed and tested with EM340-DIN 3-Phase Energy Meter from Carlo Gavazzi.
Tested on Rasbian Jessie. DIY RS-232 interface at 24 Volt and Profilic USB to RS-232 adapter.

## Futures
Reads the data frames from device id:1

## Support
Not likley.

# Usage
I recommend that you first test your setup with CuteCom so you are sure your hardware works
before using the plugin. (image needed)
Create a folder "MbusSerial" in Domotics/Plugins and copy plugin.py there.
Restart Domoticz.
Consult your meters M-Bus manual to decide which variable you want to use with wich Device.
Setting Debug to "All Steps" will output to Domoticz log.


### Build Status

Thrown together with no respect at all for Python3 or standards.

