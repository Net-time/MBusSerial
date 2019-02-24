#           M-Bus (Meter-bus) Example Plugin
#
#           Author:     Net-Time, 2018
#
# TODO: use accessnr to doublecheck correct frame
#
#   Plugin parameter definition below will be parsed during startup and copied into Manifest.xml,
#   this will then drive the user interface in the Hardware web page
#
"""
<plugin key="MBus" name="MBusSerial" author="Net-time" version="0.4.2" externallink="https://github.com/Net-time/MBusSerial">
    <description>
        <h2>M-Bus (Meter Bus) Serial Master</h2><br/>
    </description>
    <params>
        <param field="SerialPort" label="Serial Port" width="150px" required="true" default="/dev/ttyUSB0"/>
        <param field="Mode1" label="Frames to fetch" width="150px" required="true" default="1"/>
        <param field="Mode2" label="Device Type" width="200px">
            <options>
                <option label="1 Phase Ampere" value="0" />
                <option label="3 Phase Ampere" value="1" default= true/>
                <option label="KWh (Instant+Counter)" value="2"/>               
                <option label="Water" value="3"/>
                <option label="Energy Smart Meter" value="4"/>
            </options>
        </param>
        <param field="Mode3" label="Variable 1" width="150px" required="true" default="8"/>
        <param field="Mode4" label="Variable 2" width="150px" required="true" default="9"/>
        <param field="Mode5" label="Variable 3" width="150px" required="true" default="10"/>
        
        <param field="Mode6" label="Log Debug" width="100px">
            <options>
                <option label="All steps" value="Debug"/>
                <option label="Minimal" value="Normal"  default="true" />
            </options>
        </param>
    </params>
</plugin>
"""
import Domoticz
import subprocess
#import time
import binascii



SerialConn = None
message = bytearray(0)
frames = 1
variableDict ={}
endOfFrame = 19 # Minumum Frame length set for workLoop 2
workLoop =0 # 0 initiate, 1 waiting for reply, 2 Initiate Success, 3 Request Frame, 4 Frame read success, parse data, 5 delay
vifDict = {'05': {'Unit': 'Wh', 'factor': 100.0}, 
            '0413': {'Unit': 'm3' , 'factor': 1.0},
            '053e': {'Unit': 'm3h' , 'factor': 1.0},
            '055b': {'Unit': 'C' , 'factor': 1.0},
            '2a': {'Unit': 'W' , 'factor': 0.1},
            'a674': {'Unit': 'H' , 'factor': 0.01},
            'fd48': {'Unit': 'V' , 'factor': 0.1},
            'fd59': {'Unit': 'A' , 'factor': 0.001},
            'fdba73': {'Unit': 'PF' , 'factor': 0.001},
            'fb2e': {'Unit': 'Hz' , 'factor': 0.1},
            'fb8275': {'Unit': 'Kvarh' , 'factor': 100.0},
            'fb9772': {'Unit': 'Kvar' , 'factor': 0.0001},
            'fbb772': {'Unit': 'kVA' , 'factor': 0.0001}}

def onStart():
    global SerialConn

    if (len(Devices) == 0):
        Domoticz.Log("Device creation.")
        if Parameters["Mode2"] == "0":
            Domoticz.Device(Name="1-Phase", Unit=1, TypeName="Current (Single)").Create()
        if Parameters["Mode2"] == "1":
            Domoticz.Device(Name="3-Phase", Unit=1, Type=89, Subtype=1, Switchtype=0, Image=0, Options="").Create()
        if Parameters["Mode2"] == "2":
            Domoticz.Device(Name="KWh", Unit=1, Type=243, Subtype=29, Switchtype=0, Image=0, Options="").Create()
        if Parameters["Mode2"] == "3":
            Domoticz.Device(Name="Water", Unit=1, Type=243, Subtype=30, Switchtype=0, Image=0, Options="").Create()
        if Parameters["Mode2"] == "4":
            Domoticz.Device(Name="Energy", Unit=1, Type=250, Subtype=1, Switchtype=0, Image=0, Options="").Create()
        Domoticz.Log("Device created.")
    Domoticz.Log("Plugin has " + str(len(Devices)) + " devices associated with it.")
    SerialConn = Domoticz.Connection(Name="MBus", Transport="Serial", Address=Parameters["SerialPort"], Protocol='None', Baud=2400)   
    SerialConn.Connect()
    return

def onConnect(Connection, Status, Description):
    global SerialConn
    subprocess.call(["stty -F /dev/ttyUSB0 min 0 time 10 -parodd parenb"],shell=True)
    if (Status == 0):
        Domoticz.Log("Connected successfully to: "+Parameters["SerialPort"])
        SerialConn = Connection
    else:
        VerBose("Failed to connect ("+str(Status)+") to: "+Parameters["SerialPort"]+" with error: "+Description)
    return True

def onMessage(Connection, Data):
    global message , workLoop, endOfFrame
    message.extend(Data)    
    # TODO send debug? message if rouge data
    #Domoticz.Log("onMessage: Data received")
    if workLoop == 1 and (Data == b'\xE5'):
        Domoticz.Log ('EM340 initiated-' + str(binascii.hexlify(Data)))
        workLoop = 2
        endOfFrame = 19 # Minumum Frame length set for workLoop 2
        message = bytearray(0)
    if workLoop == 3 or workLoop == 6:
        if len(message) == 1:
            endOfFrame = 19 # Minumum Frame length set for workLoop 2
        # Check if valid M-Bus Start and length bytes
        if len(message) == 4:
            if message[0] == message[3]: #M-bus duplicate start byte.
               if message[0] != int('68',16):
                   workLoop = 0
                   Domoticz.Log('ERROR! Start Byte not 68 hex. Reinitializing!' + str(message[0]))
                    
            if message[1] == message[2]: #M-bus duplicate data block length.
                endOfFrame = int(str(message[1])) + 6 # Total Frame length includes 4 leading bytes and 2 trailing'
                VerBose('Frame length:'+ str(endOfFrame))
            else:
                workLoop = 0
                Domoticz.Log('ERROR! Data length check Failed. Reinitializing!')
            
        if len(message) == (endOfFrame):
            VerBose ('checking Checksum')            
            # Test checksum
            checksum = 0
            #bytestring not defined?
            for el in message[4:len(message)-2]:
                checksum += el
                bytestring = checksum.to_bytes(4, 'little')
            VerBose(str(bytestring[0])+" : "+str(message[-2]))
            if  bytestring[0] and message[-2]:
                VerBose(str('Checksum OK! From Unit:' + str(int(message[5]))))
                VerBose('Message-' + str(binascii.hexlify(message)))
                VerBose("access nr:" + str(message[15]))
                workLoop += 1
            else:
                Domoticz.Log('ERROR! Checksum check Failed. Reinitializing!')
                workLoop = 0
        if len(message) >= (endOfFrame +1): #Should not be possible but anyway...
            Domoticz.Log('read too much data')
    return

def onDisconnect(Connection):
    for Device in Devices:
        Devices[Device].Update(nValue=Devices[Device].nValue, sValue=Devices[Device].sValue, TimedOut=1)
    Domoticz.Log("Connection '"+Connection.Name+"' disconnected.")
    return

def onHeartbeat():
    global SerialConn, message, workLoop , vifDict, variableDict, frames
    VerBose("workLoop="+str(workLoop))
    if (SerialConn.Connected()):
        if workLoop >= 8:
            updateDevice()
            workLoop= 0        
        if workLoop == 4:
            if ParseFrame(message) and Parameters["Mode1"] != str(frames):
                frames +=1
                message = bytearray(0)
                workLoop = 2
            else:
                workLoop = 8
            VerBose('Variables in Frame #1: 0-' + str(len(variableDict.items())-1))
            
        if workLoop == 3:
            Domoticz.Log("Frame #"+str(frames)+ " read Timeout: Reinitzilising ")
            workLoop = 0
            
        if workLoop == 2:
            VerBose("Sending read command Frame #" + str(frames))
            if frames & 1:
                SerialConn.Send("\x10\x7B\x01\x7C\x16")
            else:
                SerialConn.Send("\x10\x5B\x01\x5C\x16")
            workLoop = 3
            VerBose ("workLoop="+str(workLoop))
            
        if workLoop == 1:
            Domoticz.Log("Init read Timeout: Reinitzilising ")
            workLoop = 0            #TODO init timeout
            
        if workLoop == 0:
            variableDict ={}
            frames = 1
            VerBose("Sending init command: ")
            message = bytearray(0)
            SerialConn.Send("\x10\x40\x01\x41\x16")
            workLoop = 1
            
    else:
        SerialConn.Connect()
    return True

def ParseFrame(message):
    global vifDict, variableDict
    if True:
        if True:
            skip = 0
            dataloop=0
            subUnit=""
            variableNr=len(variableDict.items())
            moreData = True

            for xByte in range(19,len(message)-2):
                if xByte > (len(message)-5): #No more Data
                    checkMDH = len(message)-1-xByte
                    VerBose('Remaining bytes after Data: '+ str(checkMDH))
                    if checkMDH == 3:
                        if message[xByte+1] == int('1F',16):
                            VerBose('Not the last frame')
                        else:
                            if message[xByte+1] ==int('0F',16):
                                moreData = False
                                VerBose('Last frame')
                            else:
                                Domoticz.Log('Error Parsing MoreDataHolder:')
                    else:
                            if xByte == 2:
                                moreData = False
                                VerBose('No MDH, Last frame')
                            else:
                                Domoticz.Log('Error Frame Lenght')
                        
                    break
        
                if xByte <  skip: # skip parsing Data bytes allready read
                    continue
                elif dataloop == 4:
                    temp = message[xByte:xByte+(dif-1)] #TODO will error if dif =0 or dif = 5 or dif >=8
                    if dif == 6 or dif == 7: dif -=1
                    data = float(int.from_bytes(temp, byteorder='little'))
                    unit = 'Unknown VIF'
                    if vifStr in vifDict:
                        data = data*float(str(vifDict[(vifStr)]['factor']))
                        unit = vifDict[vifStr]['Unit']
                    else:
                        Domoticz.Log('Unknown factor, displaying raw data')
                    send=('{0:.1f}'.format(data))                        
                    variableDict[variableNr]['Data'] = send
                    Domoticz.Log(str(variableNr)+ '-'+ str(send)+':'+str(unit))
                    skip = xByte + dif
                    dataloop = 0
                    subUnit=""
                    variableNr +=1

                elif dataloop == 3:
                    temp2 =message[xByte]
                    vifStr=vifStr+ (hex(temp2)[2:].zfill(2))                   
                    strData = format( int(message[xByte]), 'b').zfill(8)
                    #VerBose('VIFE,'+strData)
                    if (message[xByte] & (1<<7)) :
                        dataloop =3
                    else:
                        dataloop =4        
                elif dataloop == 2:
                    temp2 =message[xByte]
                    vifStr= (hex(temp2)[2:].zfill(2))
                    strData = format( int(message[xByte]), 'b').zfill(8)
                    #VerBose('VIF ,'+strData)
                    if (message[xByte] & (1<<7)) :
                        dataloop =3
                    else:
                        dataloop =4
                elif dataloop == 1:
                    binaryStr = format(message[xByte],'08b')                    
                    if subUnit == "":
                        subUnit = binaryStr[1]
                    else:
                        subUnit = binaryStr[1] + subUnit
                        
                    strData = format( int(message[xByte]), 'b').zfill(8)
                    #VerBose('DIFE,'+strData)
                    if (message[xByte] & (1<<7)) :
                        dataloop =1
                    else:
                        dataloop =2
                elif dataloop == 0:
                    binaryStr = format(message[xByte],'08b')
                    dif = int (binaryStr[4:8],2)
                    variableDict[variableNr] = {}
                    strData = format( int(message[xByte]), 'b').zfill(8)
                    #VerBose(str('DIF ,')+strData)
                    if (message[xByte] & (1<<7)) :
                        dataloop =1
                    else:
                        dataloop =2

    return moreData

def updateDevice():
    var1= str(variableDict[int(Parameters["Mode3"])]['Data'])
    var2= str(variableDict[int(Parameters["Mode4"])]['Data'])
    var3= str(variableDict[int(Parameters["Mode5"])]['Data'])
    for p_id, p_info in variableDict.items():
        tempStr="Var:"+str( p_id)
        for key in p_info:
            tempStr2 = str( p_info[key])
            tempStr=(tempStr+' '+ key + ':'+ tempStr2.ljust(12))
            VerBose(tempStr)
    if Parameters["Mode2"] == "0":
        send = var1
        Devices[1].Update(nValue=0, sValue=send)
    if Parameters["Mode2"] == "1":
        send = var1 +';' + var2 +';'+var3
        Devices[1].Update(nValue=0, sValue=send)
    if Parameters["Mode2"] == "2":
        send = var1+';' + var2
        Devices[1].Update(nValue=0, sValue=send)
    if Parameters["Mode2"] == "3":
        send = var1
        Devices[1].Update(nValue=0, sValue=send)
    if Parameters["Mode2"] == "4":
        tempstr = var1
        tempfloat = float(tempstr)
        send = str(int(tempfloat))+';0'+';0'+';0;'+ var2 +';0'
        Devices[1].Update(nValue=0, sValue=send)
    Domoticz.Log("Received from unit#1: " + send)
    return

def VerBose(text):
    if Parameters["Mode6"] != "Normal":
        Domoticz.Log(text)
    return