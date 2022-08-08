import serial
import time
import struct
import numpy as np

# bytes = bytearray([0xAA, 0xBB, 0x0, 0x0, 0x0, 0x0, 0x1, 0x1, 0x0, 0x0, 0x9, 0x0, 0x0, 0x0])
sp = serial.Serial(port="/dev/pts/1")
#socat -ddd pty,raw,echo=0 pty,raw,echo=0

nsamples = 2000
Fs = 1000
F1 = 1
F2 = 50
F3 = 44
A = 1024
index = 0

ttt = np.arange(nsamples, dtype=np.float64) / Fs
data = A*np.sin(2*np.pi*F1*ttt) + A*np.sin(2*np.pi*F2*ttt) + A*2*np.sin(2*np.pi*F3*ttt)
data += A*np.random.normal(size=data.shape)/20

oldTime = time.perf_counter()
while 1:
    curTime = time.perf_counter()
    timeDelta = curTime - oldTime
    if (timeDelta > 0.001):
        oldTime = curTime
        
        bytes = struct.pack('<BBlll', 0xAA,0xBB, -index, index, int(data[index]))
        sp.write(bytes)

        index += 1
        if index == nsamples:
            index = 0
