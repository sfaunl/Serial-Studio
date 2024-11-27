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

class CheckSum:
    NONE              = 0
    CRC16_CRITT_FALSE = 1

    def getSize(self, aCheckSum):
        lCheckSumSize = [0, 2]
        return lCheckSumSize[aCheckSum]

    def getParserChar(self, aCheckSum):
        lParserChar = ['B', 'H']
        return lParserChar[aCheckSum]

    def calculateCRC16_CRITT_FALSE(self, aData: bytearray) -> int:
        poly = 0x1021
        init = 0xFFFF
        crc = init
        for byte in aData:
            crc ^= (byte << 8)  # Shift byte to align with the upper byte of crc
            for _ in range(8):
                if crc & 0x8000:  # Check the highest bit
                    crc = (crc << 1) ^ poly
                else:
                    crc <<= 1
                crc &= 0xFFFF  # Ensure crc is 16 bits
        return crc

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
                 aCheckSum:CheckSum,
                 aEndianness:Endianness = Endianness.LITTLE,
                 aEndSequence = [],
                 aEnableDebug = 0):

        self.buffer             = bytearray()
        self.debug              = aEnableDebug
        self.setParserScheme(aStartSequence, aDataType, aNumChannel, aCheckSum, aEndianness, aEndSequence)
        self.packetRate         = 0
        self.packetCount        = 0
        self.startTime          = 0
        self.parserErrCount     = 0
        self.parserErrRate      = 0

    def setParserScheme(self, aStartSequence,
                        aDataType:DataType,
                        aNumChannel,
                        aCheckSum:CheckSum = CheckSum.NONE,
                        aEndianness:Endianness = Endianness.LITTLE,
                        aEndSequence = []):

        self.dataType           = aDataType
        self.numChannels        = aNumChannel
        self.startSequence      = aStartSequence
        self.checkSum           = aCheckSum
        self.endSequence        = aEndSequence
        self.endianness         = aEndianness

        self.payloadSize        = self.numChannels * DataType().getSize(self.dataType)
        self.headerSize         = len(self.startSequence)
        self.checkSumSize       = CheckSum().getSize(self.checkSum)
        self.packetSize         = self.headerSize + self.payloadSize + self.checkSumSize + len(self.endSequence)

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
                if self.buffer[i + self.headerSize + self.payloadSize + self.checkSumSize] != val:
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

            # check checksum
            if self.checkSum == CheckSum.CRC16_CRITT_FALSE:
                lReceivedPacket = self.buffer[:self.packetSize]
                lData = bytearray(lReceivedPacket[:self.headerSize + self.payloadSize])
                lByteOrder = 'little' if self.endianness == Endianness.LITTLE else 'big'
                lCrcInt = int.from_bytes(lReceivedPacket[-2:], byteorder=lByteOrder)
                lCalculatedInt = CheckSum().calculateCRC16_CRITT_FALSE(lData)
                if lCalculatedInt != lCrcInt:
                    #print("Received data:", " ".join(f"0x{byte:02X}" for byte in lReceivedPacket))
                    #print("CRC Error, got: {0:04X}, expected: {1:04X}".format(lCrcInt, lCalculatedInt))
                    self.parserErrCount += 1
                    self.buffer = self.buffer[self.packetSize:]
                    continue

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
    print("This is a library file, please import it to use.")
