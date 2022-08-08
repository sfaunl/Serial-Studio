import serial
import time
import struct
import numpy as np

# bytes = bytearray([0xAA, 0xBB, 0x0, 0x0, 0x0, 0x0, 0x1, 0x1, 0x0, 0x0, 0x9, 0x0, 0x0, 0x0])
sp = serial.Serial(port="/dev/pts/1")
#socat -ddd pty,raw,echo=0 pty,raw,echo=0

nsamples = 2000
Fs = 7500
F1 = 1
F2 = 1250
F3 = 2499
F4 = Fs/2 - 1
A = 32
index = 0

ttt = np.arange(nsamples, dtype=np.float64) / Fs
data = A*np.sin(2*np.pi*F1*ttt)
data += A*np.sin(2*np.pi*F2*ttt)
data += A*np.sin(2*np.pi*F3*ttt)
data += A*np.sin(2*np.pi*F4*ttt)
data += A*np.random.normal(size=data.shape)

oldTime = time.perf_counter()
while 1:
    curTime = time.perf_counter()
    timeDelta = curTime - oldTime
    if (timeDelta > 1/Fs):
        oldTime = curTime
        
        bytes = struct.pack('<BBlll', 0xAA,0xBB, -index, index, int(data[index]))
        sp.write(bytes)

        index += 1
        if index == nsamples:
            index = 0
