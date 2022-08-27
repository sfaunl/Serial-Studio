"""
Created on Sat Apr 23 02:02:34 2022

@file: serialparser.py
@author: Sefa Unal
"""
import struct
import time

class Endianness:
    LITTLE  = 0
    BIG     = 1
    
    def getParserChar(self, aEndianness):
        lParserChar = ['<', '>']
        return lParserChar[aEndianness]
    
class DataType:
    INT8    = 0
    UINT8   = 1
    INT16   = 2
    UINT16  = 3
    INT32   = 4
    UINT32  = 5
    INT64   = 6
    UINT64  = 7
    FLOAT   = 8
    DOUBLE  = 9
    
    def getSize(self, aDataType):
        lDataSize = [1, 1, 2, 2, 4, 4, 8, 8, 4, 8]
        return lDataSize[aDataType]
    
    def getParserChar(self, aDataType):
        lParserChar = ['b', 'B', 'h', 'H', 'l', 'L', 'q', 'Q', 'f', 'd']
        return lParserChar[aDataType]

class SerialParser:
    def __init__(self, aStartSequence, 
                 aDataType:DataType, 
                 aNumChannel, 
                 aEndianness:Endianness = Endianness.LITTLE,
                 aEndSequence = [],
                 aEnableDebug = 0):
        
        self.buffer             = bytearray()
        self.debug              = aEnableDebug
        self.setParserScheme(aStartSequence, aDataType, aNumChannel, aEndianness, aEndSequence)
        self.packetRate         = 0
        self.packetCount        = 0
        self.startTime          = 0
        self.parserErrCount     = 0
        self.parserErrRate      = 0

    def setParserScheme(self, aStartSequence, 
                        aDataType:DataType, 
                        aNumChannel, 
                        aEndianness:Endianness = Endianness.LITTLE, 
                        aEndSequence = []):
        
        self.dataType           = aDataType
        self.numChannels        = aNumChannel
        self.startSequence      = aStartSequence
        self.endSequence        = aEndSequence
        self.endianness         = aEndianness
        
        self.payloadSize        = self.numChannels * DataType().getSize(self.dataType)
        self.headerSize         = len(self.startSequence)
        self.packetSize         = self.headerSize + self.payloadSize + len(self.endSequence)
        
        self.parserString       = Endianness().getParserChar(self.endianness)
        for i in range(self.numChannels):
            self.parserString += DataType().getParserChar(self.dataType)
        
    def getPacketRate(self):
        return self.packetRate
    
    def getErrorRate(self):
        return self.parserErrRate // self.packetSize

    def getExpected(self):
        explst = []
        explst.extend(self.startSequence)
        for i in range(self.numChannels * DataType().getSize(self.dataType)):
            explst.append('XX')
        explst.extend(self.endSequence)
        return str(explst)
        
    def parse(self, data):
        parsedPackets = []
        self.buffer.extend(data)
        
        while len(self.buffer) >= self.packetSize:
            lNotFound = 0
            # search for start sequence
            for i, val in enumerate(self.startSequence):
                if self.buffer[i] != val :
                    lNotFound = 1
                    break
            
            if lNotFound:
                # remove a byte and search again
                self.buffer.pop(0)
                self.parserErrCount += 1
                continue
            
            # search for end sequence
            for i, val in enumerate(self.endSequence):
                if self.buffer[i + self.headerSize + self.payloadSize] != val :
                    lNotFound = 1
                    break
                
            if lNotFound:
                # remove a byte and search again
                self.buffer.pop(0)
                self.parserErrCount += 1
                continue
            
            # found a valid packet
            byteRange = self.buffer[self.headerSize:self.headerSize + self.payloadSize]
            parsedValues = struct.unpack(self.parserString, byteRange)
            parsedPackets.append(parsedValues)
            
            # remove parsed packet from buffer
            self.buffer = self.buffer[self.packetSize:]

        # calculate incoming packet/error rate 
        self.packetCount += len(parsedPackets)
        curTime = time.perf_counter()
        if self.startTime == 0:
            self.startTime = curTime
        else:
            timeDelta = curTime - self.startTime
            if timeDelta > 1: # calculate packetpersecond value every second
                self.packetRate = self.packetRate * 0.3 + (self.packetCount / timeDelta) * 0.7
                self.packetCount = 0;
                self.parserErrRate = self.parserErrRate * 0.3 + (self.parserErrCount / timeDelta) * 0.7
                self.parserErrCount = 0
                
                self.startTime = curTime
                
        # Transpose of parsedPackets
        parsedPackets = list(map(list, zip(*parsedPackets)))
        return parsedPackets

if __name__ == '__main__':
    print("bye")