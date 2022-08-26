
import time, serial, struct, sys, subprocess, numpy as np

def start_socat():
    print("Starting socat process...")
    socatcmd = "socat -dd pty,raw,echo=0 pty,raw,echo=0"
    socatproc = subprocess.Popen(socatcmd.split(" "), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # parse output of socat process
    ptylist = []
    for i, line in enumerate(socatproc.stderr):
        line = line.decode().strip()
        searchstr = "N PTY is"
        offset = line.find(searchstr)
        if offset != -1:
            ptylist.append( line[offset + len(searchstr) + 1 : ] )
            if len(ptylist) == 2:
                break
        if i > 10:
            break

    if socatproc.poll() is not None:
        print("Error starting socat...")
        exit(2)

    return ptylist

def send_bytes(ptylist):
    portname = ptylist[0]
    try:
        sp = serial.Serial(port = portname)

        print("Starting to transmit on: ", portname)
        if len(ptylist) > 1:
            print("Receive on port: ", ptylist[1])

        nsamples = 2000
        Fs = 10000
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
    except Exception as error: 
        print("Error opening \'" + portname + "\'")


USAGE = f"Usage: \n" \
        f"  python {sys.argv[0]} --port <portname>\n" \
        f"  python {sys.argv[0]} --socat\n" \
        f"  python {sys.argv[0]} --version\n" \
        f"  python {sys.argv[0]} --help"
VERSION = "0.2"

if __name__ == "__main__":
    ptylist = []

    opts = [opt for opt in sys.argv[1:] if opt.startswith("-")]
    args = [arg for arg in sys.argv[1:] if not arg.startswith("-")]
    
    if len(opts) == 0:
        raise SystemExit(USAGE)
    if opts[0] == "-h" or opts[0] == "--help":
        raise SystemExit(USAGE)
    elif opts[0] == "-v" or opts[0] == "--version":
        raise SystemExit(VERSION)
    elif opts[0] == "-p" or opts[0] == "--port":
        if len(args) == 0:
            print("Portname is missing...")
            raise SystemExit(USAGE)
        ptylist.append(args[0])
    elif opts[0] == "-s" or opts[0] == "--socat":
        ptylist = start_socat()
        if len(ptylist) == 0:
            raise SystemExit("Cannot retrieve portnames")
    elif sys.argv[1:]:
        raise SystemExit(USAGE)
    
    send_bytes(ptylist)