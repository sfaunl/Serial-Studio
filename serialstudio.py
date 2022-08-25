"""
Created on Sat Apr 23 02:08:23 2022

@file       serialstudio.py
@brief      Serial data visualizer
@author     Sefa Unal

@version    0.2.2
@date       25/08/2022
@since		v0.1 : initial release
@since		v0.2 : add multiplier and offset
@since		v0.2.1 : fix loading incorrect parameters
@since		v0.2.2 : add plot screenshot functionality (thanks to 220523)
"""

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import *

import pyqtgraph as pg
import pyqtgraph.parametertree as ptree
import pyqtgraph.exporters

import sys
import time
import serial
import serial.tools.list_ports as lp
import numpy as np
from scipy.fftpack import fft
import json

import serialparser as sp

class ConfigParser():
    def __init__(self, filename = "config.json"):
        self.configfile = filename

    def loadConfig(self):
        try:
            with open(self.configfile) as json_config_file:
                data = json.load(json_config_file)
                return data
        except:
            return

    def saveConfig(self, parameters:dict):
        try:
            with open(self.configfile, "w") as json_config_file:
                json.dump(parameters, json_config_file, indent=2)
            return True
        except:
            return False


class SerialStudio(QtWidgets.QWidget):
    appname = "Serial Studio"
    version = "0.2.1"

    parameters = {
        'conn': {
            'portname': '',
            'baudrate': 115200,
            'databits': 8,
            'stopbits': 1,
            'parity': 'N'
        },
        'parser': {
            'startbyte': [0xAA, 0xBB],
            'endbyte': [],
            'channel': 3,
            'datatype': 4,
            'endianness': 0
        },
        'channels': {
            'activechs': [0, 1, 2],
            'inactivechs': []
        },
        'plotter': {
            'autoscale': True,
            'buffersize': 4096,
            'offset': 0,
            'multiplier': 1
        },
        'fft': {
            'autoscale': True,
            'showdc': False,
            'fftsize': 1024
        }
    }

    ptchildren = [
        dict(name='connect', title='Connect', type='action', children=[
            dict(name='connected', title='Connected', type='str', value='', readonly=True, visible=False),
        ]),
        dict(name='serialopts', title='Connection', type='group', children=[
            dict(name='Custom Port', type='bool', value=False, enabled=True),
            dict(name='PortList', title='Port', type='list', visible=True),
            dict(name='PortStr', title='Port', type='str', value="/dev/pts/2", visible=False),
            dict(name='BaudRate', type='int', limits=[0, None], value=115200),
            dict(name='Data Bits', type='list', limits=[5, 6, 7, 8], value=8),
            dict(name='Stop Bits', type='list', limits=[1, 1.5, 2], value=1),
            dict(name='Parity', type='list', limits={'None': 'N', 'Even': 'E', 'Odd': 'O', 'Mark': 'M', 'Space': 'S'}, value='N'),
        ]),
        dict(name='parseropts', title='Parser Options', type='group', children=[
            dict(name='StartByte', type='str', value="AA BB"),
            dict(name='EndByte', type='str', value=""),
            dict(name='Channels', type='int', limits=[0, 10], value=3),
            dict(name='DataType', type='list', limits={'INT8': 0, 'UINT8': 1,
                                                       'INT16': 2, 'UINT16': 3,
                                                       'INT32': 4, 'UINT32': 5,
                                                       'INT64': 6, 'UINT64': 7,
                                                       'FLOAT': 8, 'DOUBLE': 9}, value=4),
            dict(name='Endianness', type='list', limits={'LITTLE': 0, 'BIG': 1}, value=0),
            dict(name='Expected', type='str', value='', readonly=True),
        ]),
        dict(name='channelopts', title='Channels', type='group'),
        dict(name='plotteropts', title='Plotter Options', type='group', children=[
            dict(name='Autoscale', type='bool', value=True, enabled=False),
            dict(name='Plot Length', type='int', limits=[0, None], step=1000, value=4096),
            dict(name='Multiplier', type='float', value=1.0, precision=2),
            dict(name='Offset', type='float', value=0.0, precision=2),
        ]),
        dict(name='fftopts', title='FFT Options', type='group', children=[
            dict(name='Autoscale', type='bool', value=True, enabled=False),
            dict(name='Show DC', type='bool', value=False),
            dict(name='NSamples', type='int', limits=[0, None], value=1024),
        ]),
        dict(name='stats', title='Stats', type='group', children=[
            dict(name='Packet/s', type='int',value=0, readonly=True, units='pps'),
            dict(name='Error/s', type='int',value=0, readonly=True, units='pps'),
            dict(name='Queue', type='int', value=0,readonly=True, units='bytes'),
        ]),
    ]

    def __init__(self, debug=False):
        super().__init__()
        self.debug = debug
        self.ser = None
        self.queue = 0
        self.chdata = []

        self.defaultParams = self.parameters
        self.config = ConfigParser()
        self.initUI()
        self.initParser()
        configLoaded = self.loadconfig()
        if configLoaded == False:
            # init paramtree values manually
            self.paramSerialChanged()
            self.paramParserChanged()
            self.paramPlotterChanged()
            self.paramFftChanged()
            self.paramChannelChanged()

    def initUI(self):
        # Parameter tree object
        self.params = ptree.Parameter.create(name='Parameters', type='group', children=self.ptchildren)
        paramtree = ptree.ParameterTree(showHeader=False)
        paramtree.setParameters(self.params)

        self.params.child('channelopts').sigTreeStateChanged.connect(self.paramChannelChanged)
        self.params.child('serialopts').sigTreeStateChanged.connect(self.paramSerialChanged)
        self.params.child('parseropts').sigTreeStateChanged.connect(self.paramParserChanged)
        self.params.child('plotteropts').sigTreeStateChanged.connect(self.paramPlotterChanged)
        self.params.child('fftopts').sigTreeStateChanged.connect(self.paramFftChanged)
        self.params.child('connect').sigActivated.connect(self.connect)

        # plotter object
        self.glw = pg.GraphicsLayoutWidget()

        self.plotter_t = self.glw.addPlot(row=0, col=0)
        self.plotter_t.setMouseEnabled(x=True, y=False)
        self.plotter_t.setLabel('left', 'amplitude', units='v')
        self.plotter_t.setLabel('bottom', 'time', units='s')
        self.plotter_t.enableAutoRange(axis = 'x')
        legendt = self.plotter_t.addLegend()
        legendt.anchor((1, 0), (1, 0))
        self.plotter_f = self.glw.addPlot(title="FFT", row=1, col=0)
        self.plotter_f.setMouseEnabled(x=True, y=False)
        self.plotter_f.setLabel('left', 'amplitude', units='v')
        self.plotter_f.setLabel('bottom', 'freq', units='Hz')
        self.plotter_f.enableAutoRange(axis = 'x')
        legendf = self.plotter_f.addLegend()
        legendf.anchor((1, 0), (1, 0))

        vbox = QtWidgets.QVBoxLayout(self)
        self.statusBar = QtWidgets.QStatusBar(self)

        splitter = QtWidgets.QSplitter(self)
        splitter.addWidget(paramtree)
        splitter.addWidget(self.glw)

        # menu-bar
        menu_bar = QtWidgets.QMenuBar()
        file_menu = menu_bar.addMenu('File')
        capture_action = QAction('Capture Plot', self)
        capture_action.setShortcut("CTRL+E")
        capture_action.setIcon(QtGui.QIcon.fromTheme('insert-image'))
        capture_action.triggered.connect(self.captureplot)
        exit_action = QAction('Exit', self)
        exit_action.setShortcut("CTRL+Q")
        exit_action.setIcon(QtGui.QIcon.fromTheme('application-exit'))
        exit_action.triggered.connect(exit)
        file_menu.addAction(capture_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        config_menu = menu_bar.addMenu('Config')
        save_action = QAction('Save Config', self)
        save_action.setShortcut("CTRL+S")
        save_action.setIcon(QtGui.QIcon.fromTheme('document-save'))
        save_action.triggered.connect(self.saveconfig)
        load_action = QAction('Load Config', self)
        load_action.setIcon(QtGui.QIcon.fromTheme('document-open'))
        load_action.triggered.connect(self.loadconfig)
        restore_action = QAction('Restore Config', self)
        restore_action.setIcon(QtGui.QIcon.fromTheme('document-revert'))
        restore_action.triggered.connect(self.restoreconfig)
        config_menu.addAction(save_action)
        config_menu.addAction(load_action)
        config_menu.addAction(restore_action)

        vbox.addWidget(menu_bar)
        vbox.addWidget(splitter, 1)
        vbox.addWidget(self.statusBar)
        self.setLayout(vbox)

        self.resize(1024, 700)
        self.setWindowTitle("{} - v{}".format(self.appname, self.version))
        self.show()

    def initParser(self):
        # set parser
        self.parser = sp.SerialParser(aStartSequence=self.parameters['parser']['startbyte'],
                                      aEndSequence=self.parameters['parser']['endbyte'],
                                      aDataType=self.parameters['parser']['datatype'],
                                      aNumChannel=self.parameters['parser']['channel'],
                                      aEndianness=self.parameters['parser']['endianness'])

        # calculate X values for the plotter
        self.calculateXAxes()

        # update timers
        self.last_update = time.perf_counter()
        self.mean_dt = None

        # 60Hz
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(16)
        # 2Hz
        self.timerui = QtCore.QTimer()
        self.timerui.timeout.connect(self.updateui)
        self.timerui.start(500)

    def calculateXAxes(self):
        # calculate X values for the plotter
        ltplotlength = self.parameters['plotter']['buffersize']
        lfNSamples = self.parameters['fft']['fftsize']
        pps = self.parser.getPacketPerSecond()
        T = 0.001
        if pps != 0:
            T = 1 / self.parser.getPacketPerSecond()  # 0.001
        self.Xt = np.linspace(0.0, ltplotlength * T, ltplotlength)
        self.Xf = np.linspace(0.0, 1.0 / (2 * T),   lfNSamples // 2)

    def saveconfig(self):
        retval = self.config.saveConfig(self.parameters)
        if retval:
            msg = "Config file saved"
            self.statusBar.showMessage(msg)
            print(msg)
        else:
            msg = "Error saving config file"
            self.statusBar.showMessage(msg)
            print(msg)
        
    def loadconfig(self):
        params = self.config.loadConfig()
        if params:
            self.parameters = params
            self.loadParameters()
            msg = "Config file loaded"
            self.statusBar.showMessage(msg)
            print(msg)
            return True
        else:
            msg = "Error loading config file"
            self.statusBar.showMessage(msg)
            print(msg)
            return False

    def restoreconfig(self):
        self.parameters = self.defaultParams
        self.loadParameters()
        msg = "Config restored"
        self.statusBar.showMessage(msg)
        print(msg)

    def loadParameters(self):
        seropts = self.params.child('serialopts')
        parseropts = self.params.child('parseropts')
        plotteropts = self.params.child('plotteropts')
        fftopts = self.params.child('fftopts')

        #seropts
        with seropts.treeChangeBlocker():
            seropts.child('Custom Port').setValue(True)
            seropts.child('PortStr').setValue(self.parameters['conn']['portname'])
            seropts.child('BaudRate').setValue(self.parameters['conn']['baudrate'])
            seropts.child('Data Bits').setValue(self.parameters['conn']['databits'])
            seropts.child('Stop Bits').setValue(self.parameters['conn']['stopbits'])
            seropts.child('Parity').setValue(self.parameters['conn']['parity'])

        #parseropts
        with parseropts.treeChangeBlocker():
            startbytelist = self.parameters['parser']['startbyte']
            hexstr = ""
            for byte in startbytelist:
                hexstr += format(byte, 'X') + " "
            parseropts.child('StartByte').setValue(hexstr)

            endbytelist = self.parameters['parser']['endbyte']
            hexstr = ""
            for byte in endbytelist:
                hexstr += format(byte, 'X') + " "
            parseropts.child('EndByte').setValue(hexstr)
            parseropts.child('Channels').setValue(self.parameters['parser']['channel'])
            parseropts.child('DataType').setValue(self.parameters['parser']['datatype'])
            parseropts.child('Endianness').setValue(self.parameters['parser']['endianness'])

        #plotteropts
        with plotteropts.treeChangeBlocker():
            plotteropts.child('Autoscale').setValue(self.parameters['plotter']['autoscale'])
            plotteropts.child('Plot Length').setValue(self.parameters['plotter']['buffersize'])
            plotteropts.child('Multiplier').setValue(self.parameters['plotter']['multiplier'])
            plotteropts.child('Offset').setValue(self.parameters['plotter']['offset'])

        #fftopts
        with fftopts.treeChangeBlocker():
            fftopts.child('Autoscale').setValue(self.parameters['fft']['autoscale'])
            fftopts.child('Show DC').setValue(self.parameters['fft']['showdc'])
            fftopts.child('NSamples').setValue(self.parameters['fft']['fftsize'])

    def paramChannelChanged(self):
        if self.debug:
            print("paramChannelChanged")
        channelopts = self.params.child('channelopts')
        numchan = self.parameters['parser']['channel']

        # update active/inactive channels variable
        activechs = []
        inactivechs = []
        for ch in range(numchan):
            chname = "CH{}".format(ch)
            childval = channelopts.child(chname).value()
            if childval == True:
                activechs.append(ch)
            else:
                inactivechs.append(ch)
        self.parameters['channels']['activechs'] = activechs
        self.parameters['channels']['inactivechs'] = inactivechs

    def paramSerialChanged(self):
        if self.debug:
            print("paramSerialChanged")
        seropts = self.params.child('serialopts')
        customport = seropts['Custom Port']

        with seropts.treeChangeBlocker():
            if customport == True:
                seropts.child('PortStr').setOpts(visible=True)
                seropts.child('PortList').setOpts(visible=False)
                self.parameters['conn']['portname'] = seropts.child('PortStr').value()
            else:
                all_comports = lp.comports()
                ports = {}
                for port in sorted(all_comports):
                    descstr =  "{} : {}, {}".format(port.device, port.manufacturer, port.description)
                    ports[descstr] = port.device

                seropts.child('PortStr').setOpts(visible=False)
                seropts.child('PortList').setOpts(visible=True)
                seropts.child('PortList').setOpts(limits=ports)
                self.parameters['conn']['portname'] = seropts.child('PortList').value()

        self.parameters['conn']['baudrate'] = seropts.child('BaudRate').value()
        self.parameters['conn']['databits'] = seropts.child('Data Bits').value()
        self.parameters['conn']['stopbits'] = seropts.child('Stop Bits').value()
        self.parameters['conn']['parity'] = seropts.child('Parity').value()

    def paramParserChanged(self):
        if self.debug:
            print("paramParserChanged")
        parseropts = self.params.child('parseropts')
        startByteStr = parseropts.child('StartByte').value()
        self.parameters['parser']['startbyte'] = list(bytearray.fromhex(startByteStr))
        endByteStr = parseropts.child('EndByte').value()
        self.parameters['parser']['endbyte'] = list(bytearray.fromhex(endByteStr))
        numchan = parseropts.child('Channels').value()
        self.parameters['parser']['channel'] = numchan
        self.parameters['parser']['datatype'] = parseropts.child('DataType').value()
        self.parameters['parser']['endianness'] = parseropts.child('Endianness').value()

        # add/remove channel entries in parameter tree
        channelopts = self.params.child('channelopts')
        childcount = len(channelopts.children())
        with channelopts.treeChangeBlocker():
            for ch in range(max(numchan, childcount)):
                if ch >= numchan:
                    channelopts.removeChild(
                        channelopts.child("CH{}".format(ch)))
                elif ch >= childcount:
                    name = "CH{}".format(ch)
                    channelopts.addChild({'name': name, 'type': 'bool', 'value': True})

        dataitems_t = self.plotter_t.listDataItems()
        dataitems_f = self.plotter_f.listDataItems()
        numdataitems = len(dataitems_t)

        for ch in range(max(numchan, numdataitems)):
            if ch >= numchan:
                self.plotter_t.removeItem(dataitems_t[ch])
                self.plotter_f.removeItem(dataitems_f[ch])
            if ch >= numdataitems:
                # color = ['b', 'g', 'r', 'c', 'm', 'y', 'k', 'w']
                plotData = pg.PlotDataItem(pen=pg.intColor(ch, hues=10), name="CH{}".format(ch))
                # plotData = pg.PlotDataItem(pen=color[ch], name="CH{}".format(ch))
                self.plotter_t.addItem(plotData)
                plotData = pg.PlotDataItem(pen=pg.intColor(ch, hues=10), name="CH{}".format(ch))
                self.plotter_f.addItem(plotData)
                self.chdata.append([])

        # set new parser config
        self.parser.setParserScheme(aStartSequence=self.parameters['parser']['startbyte'],
                                    aEndSequence=self.parameters['parser']['endbyte'],
                                    aDataType=self.parameters['parser']['datatype'],
                                    aNumChannel=self.parameters['parser']['channel'],
                                    aEndianness=self.parameters['parser']['endianness'])

        expectedStr = self.parser.getExpected()
        parseropts.child('Expected').setValue(expectedStr)

    def paramPlotterChanged(self):
        if self.debug:
            print("paramPlotterChanged")
        plotteropts = self.params.child('plotteropts')
        self.parameters['plotter']['autoscale'] = plotteropts.child('Autoscale').value()
        self.parameters['plotter']['buffersize'] = plotteropts.child('Plot Length').value()
        self.parameters['plotter']['offset'] = plotteropts.child('Offset').value()
        self.parameters['plotter']['multiplier'] = plotteropts.child('Multiplier').value()
        self.calculateXAxes()

    def paramFftChanged(self):
        if self.debug:
            print("paramFftChanged")
        fftopts = self.params.child('fftopts')
        self.parameters['fft']['autoscale'] = fftopts.child('Autoscale').value()
        self.parameters['fft']['showdc'] = fftopts.child('Show DC').value()
        self.parameters['fft']['fftsize'] = fftopts.child('NSamples').value()
        self.calculateXAxes()

    def connect(self):
        if self.debug:
            print("Connect")
        portname = self.parameters['conn']['portname']
        baudrate = self.parameters['conn']['baudrate']
        self.parameters['conn']['baudrate']
        try:
            self.ser = serial.Serial(port=portname,
                                     baudrate=baudrate,
                                     bytesize=self.parameters['conn']['databits'],
                                     stopbits=self.parameters['conn']['stopbits'],
                                     parity=self.parameters['conn']['parity'])
        except:
            msg = "Cannot connect to: {}".format(portname)
            self.statusBar.showMessage(msg)
            print(msg)
            return

        msg = "Connected to: {} ({})".format(portname, baudrate)
        self.statusBar.showMessage(msg)
        print(msg)

        gconnect = self.params.child('connect')
        connectedstr = "{} :{}".format(portname, baudrate)
        gconnect.child('connected').setOpts(visible=True, value=connectedstr)
        gconnect.setOpts(title="Disconnect")
        gconnect.sigActivated.disconnect(self.connect)
        gconnect.sigActivated.connect(self.disconnect)
        self.params.child('serialopts').hide()
        print(self.ser)

    def disconnect(self):
        if self.debug:
            print("disconnect")
        self.ser.close()

        if self.ser.is_open == False:
            gconnect = self.params.child('connect')
            gconnect.setOpts(title="Connect")
            gconnect.sigActivated.disconnect(self.disconnect)
            gconnect.sigActivated.connect(self.connect)
            self.params.child('serialopts').show()
            self.params.child('connect').child('connected').setOpts(visible=False)

            msg = "Disconnected"
            self.statusBar.showMessage(msg)
            print(msg)
        else:
            msg = "Unable to disconnect"
            self.statusBar.showMessage(msg)
            print(msg)

    def captureplot(self):
        exporter = pg.exporters.ImageExporter( self.glw.scene() )

        filename = 'IMAG_' + time.strftime('%Y%m%d_%H%M%S')

        #exporter.parameters()['width'] = 1920
        exporter.export(filename + '.png')

        msg = 'Capture recorded as ' + filename + '.png'
        self.statusBar.showMessage(msg)
        print(msg)

    def update(self):
        timestamp = time.perf_counter()
        dt = timestamp - self.last_update
        self.last_update = timestamp
        if self.mean_dt is None:
            self.mean_dt = dt
        else:
            self.mean_dt = 0.95 * self.mean_dt + 0.05 * dt

        if self.ser == None:
            return

        if not self.ser.is_open:
            return

        lDataBuffer = None
        try:
            inw = self.ser.in_waiting
            lDataBuffer = self.parser.parse(self.ser.read(inw))

            self.queue = inw
            if inw == 0:
                return

        except:
            self.disconnect()
            print("Port disconnected...")
            return

        if len(lDataBuffer) == 0:
            return

        if len(lDataBuffer[0]) == 0:
            return

        multiplier = self.parameters['plotter']['multiplier']
        offset = self.parameters['plotter']['offset']
        for i, ch in enumerate(lDataBuffer):
            for j, data in enumerate(ch):
                data *= multiplier
                data += offset
                lDataBuffer[i][j] = data

        numch = self.parameters['parser']['channel']
        for ch in range(numch):
            self.chdata[ch].extend(lDataBuffer[ch])

        activechs = self.parameters['channels']['activechs']
        inactivechs = self.parameters['channels']['inactivechs']
        dataItems_t = self.plotter_t.listDataItems()

        # draw time domain plot
        tstart = - min(self.parameters['plotter']['buffersize'] + 1, len(self.chdata[0]))
        tend = -1

        for ch in inactivechs:
            dataItems_t[ch].clear()
        for ch in activechs:
            dataItems_t[ch].setData(
                self.Xt[0:-tstart-1], self.chdata[ch][tstart:tend])

        # draw frequency domain plot
        lfNSamples = self.parameters['fft']['fftsize']
        if(len(self.chdata[0]) > lfNSamples):
            tstart = -min(lfNSamples + 1, len(self.chdata[0]))
            fstart = 1
            if self.parameters['fft']['showdc'] == True:
                fstart = 0
            fend = (lfNSamples // 2) - 1

            dataItems_f = self.plotter_f.listDataItems()
            for ch in inactivechs:
                dataItems_f[ch].clear()
            for ch in activechs:
                self.Yf = fft(self.chdata[ch][tstart:tend])
                dataItems_f[ch].setData(self.Xf[fstart:fend], abs(self.Yf[fstart:fend]))

    def updateui(self):
        if self.parser == None:
            return
        self.params.child('stats').child('Queue').setValue(self.queue)
        self.params.child('stats').child('Packet/s').setValue(self.parser.getPacketPerSecond())
        self.params.child('stats').child('Error/s').setValue(self.parser.getErrorPerSecond())
        self.calculateXAxes()

def main():
    app = QtWidgets.QApplication(sys.argv)
    ex = SerialStudio()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
