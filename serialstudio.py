"""
Created on Sat Apr 23 02:08:23 2022

@file       serialstudio.py
@brief      Serial data visualizer
@author     Sefa Unal

@version    0.2.6
@date       18/12/2024
@since		v0.1 : initial release
@since		v0.2 : add multiplier and offset
@since		v0.2.1 : fix loading incorrect parameters
@since		v0.2.2 : add plot screenshot functionality (thanks to 220523)
@since		v0.2.3 : migrate from pyqt to pyside
@since      v0.2.4 : add crc and channel name support
@since      v0.2.5 : use new color palette
@since      v0.2.6 : add cobs, discard bytes, value view, enable fft, plot name and color support
"""

from PySide6.QtWidgets import (
    QMainWindow, QApplication,
    QStatusBar, QSplitter, QWidget, QHBoxLayout, QLabel
)
from PySide6.QtGui import QAction, QPixmap, QIcon, QPainter, QFont
from PySide6.QtCore import Qt, QTimer, QSize

import pyqtgraph as pg
import pyqtgraph.parametertree as ptree
import pyqtgraph.exporters

import os
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

def create_emoji_icon(emoji, size=16):
    """Create a QIcon from an emoji."""
    pixmap = QPixmap(size, size)  # Create a pixmap with the specified size
    pixmap.fill(Qt.transparent)  # Transparent background

    painter = QPainter(pixmap)
    font = QFont("Segoe UI Emoji", size)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, emoji)  # Draw emoji
    painter.end()

    return QIcon(pixmap)

class SerialStudio(QMainWindow):
    appname = "Serial Studio"
    version = "0.2.6"

    colorPalette = ['#e6194B', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#42d4f4', '#f032e6', '#bfef45', '#fabed4', '#469990', '#dcbeff', '#9A6324', '#fffac8', '#800000', '#aaffc3', '#808000', '#ffd8b1', '#000075', '#a9a9a9']
    defaultParams = {
        'conn': {
            'portname': '',
            'baudrate': 115200,
            'databits': 8,
            'stopbits': 1,
            'parity': 'N'
        },
        'parser': {
            'encoding': 0,
            'startbyte': [0xAA, 0xBB],
            'discardbytes': 0,
            'endbyte': [],
            'channel': 3,
            'checksum' : 0,
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
            'enable': True,
            'autoscale': True,
            'showdc': False,
            'fftsize': 1024
        },

        'channel_config': {
            'Channel_0': {
                'name':'CH0',
                'color': colorPalette[0 % len(colorPalette)]
            },
            'Channel_1': {
                'name':'CH1',
                'color': colorPalette[1 % len(colorPalette)]
            },
            'Channel_2': {
                'name':'CH2',
                'color': colorPalette[2 % len(colorPalette)]
            },
            'Channel_3': {
                'name':'CH3',
                'color': colorPalette[3 % len(colorPalette)]
            },
            'Channel_4': {
                'name':'CH4',
                'color': colorPalette[4 % len(colorPalette)]
            },
            'Channel_5': {
                'name':'CH5',
                'color': colorPalette[5 % len(colorPalette)]
            },
            'Channel_6': {
                'name':'CH6',
                'color': colorPalette[6 % len(colorPalette)]
            },
            'Channel_7': {
                'name':'CH7',
                'color': colorPalette[7 % len(colorPalette)]
            },
            'Channel_8': {
                'name':'CH8',
                'color': colorPalette[8 % len(colorPalette)]
            },
            'Channel_9': {
                'name':'CH9',
                'color': colorPalette[9 % len(colorPalette)]
            },
            'Channel_10': {
                'name':'CH10',
                'color': colorPalette[10 % len(colorPalette)]
            },
            'Channel_11': {
                'name':'CH11',
                'color': colorPalette[11 % len(colorPalette)]
            },
            'Channel_12': {
                'name':'CH12',
                'color': colorPalette[12 % len(colorPalette)]
            },
            'Channel_13': {
                'name':'CH13',
                'color': colorPalette[13 % len(colorPalette)]
            },
            'Channel_14': {
                'name':'CH14',
                'color': colorPalette[14 % len(colorPalette)]
            },
            'Channel_15': {
                'name':'CH15',
                'color': colorPalette[15 % len(colorPalette)]
            },
            'Channel_16': {
                'name':'CH16',
                'color': colorPalette[16 % len(colorPalette)]
            },
            'Channel_17': {
                'name':'CH17',
                'color': colorPalette[17 % len(colorPalette)]
            },
            'Channel_18': {
                'name':'CH18',
                'color': colorPalette[18 % len(colorPalette)]
            },
            'Channel_19': {
                'name':'CH19',
                'color': colorPalette[19 % len(colorPalette)]
            },
            'Channel_20': {
                'name':'CH20',
                'color': colorPalette[20 % len(colorPalette)]
            },
            'Channel_21': {
                'name':'CH21',
                'color': colorPalette[21 % len(colorPalette)]
            },
            'Channel_22': {
                'name':'CH22',
                'color': colorPalette[22 % len(colorPalette)]
            },
            'Channel_23': {
                'name':'CH23',
                'color': colorPalette[23 % len(colorPalette)]
            }
        }
    }

    settings_children = [
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
            dict(name='Encoding', type='list', limits={'NONE': 0, 'COBS': 1}, value=0), #HDLC, COBS
            dict(name='StartByte', type='str', value="AA BB"),
            dict(name='DiscardBytes', type='int', limits=[0, 255], value=0),
            dict(name='EndByte', type='str', value=""),
            dict(name='Channels', type='int', limits=[0, 24], value=3),
            dict(name='CheckSum', type='list', limits={'CRC_NONE': 0, 'CRC16_CRITT_FALSE': 1}, value=0),
            dict(name='DataType', type='list', limits={'INT8': 0, 'UINT8': 1,
                                                       'INT16': 2, 'UINT16': 3,
                                                       'INT32': 4, 'UINT32': 5,
                                                       'INT64': 6, 'UINT64': 7,
                                                       'FLOAT': 8, 'DOUBLE': 9}, value=4),
            dict(name='Endianness', type='list', limits={'LITTLE': 0, 'BIG': 1}, value=0),
            dict(name='Expected', type='str', value='', readonly=True),
        ]),
        dict(name='plotopts', title='Settings', type='group', children=[
            dict(name='plotteropts', title='Plotter Options', type='group', children=[
                dict(name='Autoscale', type='bool', value=True, enabled=False),
                dict(name='Plot Length', type='int', limits=[0, None], step=1000, value=4096),
                dict(name='Multiplier', type='float', value=1.0, precision=2),
                dict(name='Offset', type='float', value=0.0, precision=2),
            ]),
            dict(name='fftopts', title='FFT Options', type='group', children=[
                dict(name='Enable', type='bool', value=False),
                dict(name='Autoscale', type='bool', value=True, enabled=False),
                dict(name='Show DC', type='bool', value=False),
                dict(name='NSamples', type='int', limits=[0, None], value=1024),
            ]),
        ]),
    ]

    def __init__(self, debug=False):
        super().__init__()
        self.counter = 0
        self.startLogging = False
        self.debug = debug
        self.ser = None
        self.queue = 0
        self.dataBuffer = None
        self.chdata = []
        self.lastPacketTime = None

        self.parameters = self.defaultParams
        self.config = ConfigParser()
        self.initUI()

        # init parser
        self.parser = sp.SerialParser(aEncoding=self.parameters['parser']['encoding'],
                                      aStartSequence=self.parameters['parser']['startbyte'],
                                      aDiscardBytes=self.parameters['parser']['discardbytes'],
                                      aEndSequence=self.parameters['parser']['endbyte'],
                                      aCheckSum=self.parameters['parser']['checksum'],
                                      aDataType=self.parameters['parser']['datatype'],
                                      aNumChannel=self.parameters['parser']['channel'],
                                      aEndianness=self.parameters['parser']['endianness'])

        configLoaded = self.loadconfig()
        if configLoaded == False:
            # init paramtree values manually
            self.paramSerialChanged()
            self.paramParserChanged()
            self.paramPlotterChanged()
            self.paramFftChanged()
            self.paramChannelChanged()

        # 2Hz timer
        self.timerui = QTimer()
        self.timerui.timeout.connect(self.update_ui)
        self.timerui.start(500)

        # 60Hz timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(16)

    def initUI(self):
        # Parameter tree object
        self.sources = ptree.Parameter.create(name='Source', type='group', children=self.settings_children)
        self.channels = ptree.Parameter.create(name='Channels', type='group')

        sourcetree = ptree.ParameterTree(showHeader=False)
        sourcetree.setParameters(self.sources)
        channeltree = ptree.ParameterTree(showHeader=False)
        channeltree.setParameters(self.channels)

        self.channels.sigTreeStateChanged.connect(self.paramChannelChanged)
        self.sources.child('serialopts').sigTreeStateChanged.connect(self.paramSerialChanged)
        self.sources.child('parseropts').sigTreeStateChanged.connect(self.paramParserChanged)
        self.sources.child('plotopts').child('plotteropts').sigTreeStateChanged.connect(self.paramPlotterChanged)
        self.sources.child('plotopts').child('fftopts').sigTreeStateChanged.connect(self.paramFftChanged)
        self.sources.child('connect').sigActivated.connect(self.serial_connect)

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

        # actions
        capture_action = QAction('Capture Plot', self)
        capture_action.setStatusTip("Save a screenshot of the plot")
        capture_action.setShortcut("CTRL+E")
        capture_action.setIcon(QIcon.fromTheme('insert-image'))
        capture_action.triggered.connect(self.captureplot)

        exit_action = QAction('Exit', self)
        exit_action.setStatusTip("Exit the application")
        exit_action.setShortcut("CTRL+Q")
        exit_action.setIcon(QIcon.fromTheme('application-exit'))
        exit_action.triggered.connect(exit)

        save_action = QAction('Save Config', self)
        save_action.setStatusTip("Save current config")
        save_action.setShortcut("CTRL+S")
        save_action.setIcon(QIcon.fromTheme('document-save'))
        save_action.triggered.connect(self.saveconfig)
        load_action = QAction('Load Config', self)
        load_action.setStatusTip("Load config")
        load_action.setIcon(QIcon.fromTheme('document-open'))
        load_action.triggered.connect(self.loadconfig)
        restore_action = QAction('Restore Config', self)
        restore_action.setStatusTip("Restore config")
        restore_action.setIcon(QIcon.fromTheme('document-revert'))
        restore_action.triggered.connect(self.restoreconfig)

        start_log_action = QAction('Start Logging', self)
        start_log_action.setStatusTip("Start logging data")
        start_log_action.setShortcut("CTRL+L")
        start_log_action.setIcon(QIcon.fromTheme('document-save'))
        start_log_action.triggered.connect(self.startlogging)
        stop_log_action = QAction('Stop Logging', self)
        stop_log_action.setStatusTip("Stop logging data")
        stop_log_action.setShortcut("CTRL+K")
        stop_log_action.setIcon(QIcon.fromTheme('document-save'))
        stop_log_action.triggered.connect(self.stoplogging)

        # menu-bar
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")
        config_menu = menu_bar.addMenu('&Config')
        log_menu = menu_bar.addMenu('&Log')

        file_menu.addAction(capture_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        config_menu.addAction(save_action)
        config_menu.addAction(load_action)
        config_menu.addAction(restore_action)

        log_menu.addAction(start_log_action)
        log_menu.addAction(stop_log_action)

        # statusbar stats
        statswidget = QWidget(self)
        hbox_stats = QHBoxLayout()
        statswidget.setLayout(hbox_stats)

        self.labellogicon = QLabel()
        labeldownicon = QLabel()
        labelerroricon = QLabel()
        labelqueueicon = QLabel()
        self.labellog = QLabel("")
        self.labelpacketrate = QLabel("0 pps")
        self.labelerrorrate = QLabel("0 pps")
        self.labelpacketqueue = QLabel("0 pps")

        self.labellogicon.setVisible(False)

        logicon = create_emoji_icon("🔴", size=16)
        downicon = create_emoji_icon("🟢", size=16)
        erroricon = create_emoji_icon("❌", size=16)
        queueicon = create_emoji_icon("🔄", size=16)

        self.labellogicon.setPixmap(logicon.pixmap(QSize(16, 16)))
        labeldownicon.setPixmap(downicon.pixmap(QSize(16, 16)))
        labelerroricon.setPixmap(erroricon.pixmap(QSize(16, 16)))
        labelqueueicon.setPixmap(queueicon.pixmap(QSize(16, 16)))

        hbox_stats.addWidget(self.labellogicon)
        hbox_stats.addWidget(self.labellog)
        hbox_stats.addWidget(labeldownicon)
        hbox_stats.addWidget(self.labelpacketrate)
        hbox_stats.addWidget(labelerroricon)
        hbox_stats.addWidget(self.labelerrorrate)
        hbox_stats.addWidget(labelqueueicon)
        hbox_stats.addWidget(self.labelpacketqueue)

        self.statusBar().addPermanentWidget(statswidget)

        # place widgets in main window
        vsplitter = QSplitter(Qt.Vertical)
        vsplitter.addWidget(sourcetree)
        vsplitter.addWidget(channeltree)
        channeltree.setMinimumHeight(250)

        splitter = QSplitter(self)
        splitter.addWidget(vsplitter)
        splitter.addWidget(self.glw)

        self.setCentralWidget(splitter)
        self.statusBar().showMessage("Ready")

        self.resize(1024, 700)
        self.setWindowTitle("{} - v{}".format(self.appname, self.version))
        self.show()

    def calculateXAxes(self):
        # calculate X values for the plotter
        ltplotlength = self.parameters['plotter']['buffersize']
        lfNSamples = self.parameters['fft']['fftsize']
        pps = self.parser.getPacketRate()
        T = 0.001
        if pps != 0:
            T = 1 / pps  # 0.001
        self.Xt = np.linspace(0.0, ltplotlength * T, ltplotlength)
        self.Xf = np.linspace(0.0, 1.0 / (2 * T),   lfNSamples // 2)

    def saveconfig(self):
        retval = self.config.saveConfig(self.parameters)
        if retval:
            msg = "Config file saved"
            self.statusBar().showMessage(msg)
            print(msg)
        else:
            msg = "Error saving config file"
            self.statusBar().showMessage(msg)
            print(msg)

    def loadconfig(self):
        params = self.config.loadConfig()
        if params:
            self.parameters = params
            self.loadParameters()
            msg = "Config file loaded"
            self.statusBar().showMessage(msg)
            print(msg)
            return True
        else:
            msg = "Error loading config file"
            self.statusBar().showMessage(msg)
            print(msg)
            return False

    def restoreconfig(self):
        self.parameters = self.defaultParams
        self.loadParameters()
        msg = "Config restored"
        self.statusBar().showMessage(msg)
        print(msg)

    def startlogging(self):
        logdirectory = "logs"

        # Ensure the log directory exists
        os.makedirs(logdirectory, exist_ok=True)

        # Generate the timestamped log file name
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        log_prefix = f"serialstudio_log_{timestamp}"
        existinglogs = [file for file in os.listdir(logdirectory) if file.endswith(".csv")]

        # Determine the next available log number
        lognumber = sum(1 for file in existinglogs if file.startswith(log_prefix))
        logfilename = "{}_{:03d}.csv".format(log_prefix, lognumber)

        # Make sure the log file does not already exist
        while logfilename in existinglogs:
            lognumber += 1
            logfilename = "{}_{:03d}.csv".format(log_prefix, lognumber)

        # Get absolute log path
        self.logfile = os.path.join(logdirectory, logfilename)
        print(f"Logging to file: {self.logfile}")

        # Open the log file and write the header
        self.logfilehandle = open(self.logfile, 'w')
        header = "\"Timestamp\", " + ", ".join(
            f"\"{self.parameters['channel_config'][f'Channel_{ch}']['name']}\""
            for ch in range(self.parameters['parser']['channel'])
        ) + "\n"
        self.logfilehandle.write(header)
        self.logfilehandle.flush()

        self.startLogging = True
        self.logStartTime = time.time()

    def stoplogging(self):
        self.startLogging = False
        self.logfilehandle.close()

    def loadParameters(self):
        seropts = self.sources.child('serialopts')
        parseropts = self.sources.child('parseropts')
        plotteropts = self.sources.child('plotopts').child('plotteropts')
        fftopts = self.sources.child('plotopts').child('fftopts')

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
            parseropts.child('Encoding').setValue(self.parameters['parser']['encoding'])
            startbytelist = self.parameters['parser']['startbyte']
            hexstr = ""
            for byte in startbytelist:
                hexstr += format(byte, '02X') + " "
            parseropts.child('StartByte').setValue(hexstr)
            parseropts.child('DiscardBytes').setValue(self.parameters['parser']['discardbytes'])

            endbytelist = self.parameters['parser']['endbyte']
            hexstr = ""
            for byte in endbytelist:
                hexstr += format(byte, '02X') + " "
            parseropts.child('EndByte').setValue(hexstr)
            parseropts.child('Channels').setValue(self.parameters['parser']['channel'])
            parseropts.child('CheckSum').setValue(self.parameters['parser']['checksum'])
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
            fftopts.child('Enable').setValue(self.parameters['fft']['enable'])
            fftopts.child('Autoscale').setValue(self.parameters['fft']['autoscale'])
            fftopts.child('Show DC').setValue(self.parameters['fft']['showdc'])
            fftopts.child('NSamples').setValue(self.parameters['fft']['fftsize'])

        #channelopts
        with self.channels.treeChangeBlocker():
            for ch in range(self.parameters['parser']['channel']):
                chtitle = self.parameters['channel_config']["Channel_{}".format(ch)]['name']
                chcolor = self.parameters['channel_config']["Channel_{}".format(ch)]['color']
                child = self.channels.child("Channel_{}".format(ch))
                child.setValue(True)
                child.child('Name').setValue(chtitle)
                child.child('Color').setValue(chcolor)

    def paramChannelChanged(self):
        if self.debug:
            print("paramChannelChanged")

        channelopts = self.channels
        with channelopts.treeChangeBlocker():
            # update active/inactive channels variable
            activechs = []
            inactivechs = []

            dataitems_t = self.plotter_t.listDataItems()
            dataitems_f = self.plotter_f.listDataItems()
            numchan = self.parameters['parser']['channel']

            # Update number of active/inactive channels
            for ch in range(numchan):
                isactive = channelopts.child("Channel_{}".format(ch)).value()
                if isactive == True:
                    activechs.append(ch)
                else:
                    inactivechs.append(ch)

            for ch in range(numchan):
                # Update the title of the plot
                oldTitle = channelopts.child("Channel_{}".format(ch)).title()
                newTitle = channelopts.child("Channel_{}".format(ch)).child('Name').value()
                chColor = channelopts.child("Channel_{}".format(ch)).child('Color').value()
                channelopts.child("Channel_{}".format(ch)).setOpts(title=newTitle)

                # This is a workaround to update the title and color of the plot
                # If active channel count does not match the number of data items displayed
                # remove the data items and add them again to update the new title and color
                if len(activechs) != len(dataitems_t):
                    if ch < len(dataitems_t):
                        self.plotter_t.removeItem(dataitems_t[ch])
                        self.plotter_f.removeItem(dataitems_f[ch])

                    isactive = channelopts.child("Channel_{}".format(ch)).value()
                    if isactive == True:
                        # Add the active plot channels
                        chColor = channelopts.child("Channel_{}".format(ch)).child('Color').value()
                        chTitle = channelopts.child("Channel_{}".format(ch)).child('Name').value()
                        plotData = pg.PlotDataItem(pen=chColor, name=chTitle)
                        self.plotter_t.addItem(plotData)
                        plotData = pg.PlotDataItem(pen=chColor, name=chTitle)
                        self.plotter_f.addItem(plotData)

                self.parameters['channel_config']["Channel_{}".format(ch)]['name'] = newTitle
                self.parameters['channel_config']["Channel_{}".format(ch)]['color'] = chColor.name()

            if len(activechs) == 0:
                self.channels.child("Select All").setOpts(visible=True)
                self.channels.child("Deselect All").setOpts(visible=False)
            else:
                self.channels.child("Select All").setOpts(visible=False)
                self.channels.child("Deselect All").setOpts(visible=True)

            self.parameters['channels']['activechs'] = activechs
            self.parameters['channels']['inactivechs'] = inactivechs

    def paramSerialChanged(self):
        if self.debug:
            print("paramSerialChanged")

        seropts = self.sources.child('serialopts')
        with seropts.treeChangeBlocker():
            customport = seropts['Custom Port']
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

    def deselectAll(self):
        for ch in range(self.parameters['parser']['channel']):
            self.channels.child("Channel_{}".format(ch)).setValue(False)

    def selectAll(self):
        for ch in range(self.parameters['parser']['channel']):
            self.channels.child("Channel_{}".format(ch)).setValue(True)

    def paramParserChanged(self):
        if self.debug:
            print("paramParserChanged")

        parseropts = self.sources.child('parseropts')
        with parseropts.treeChangeBlocker():
            self.parameters['parser']['encoding'] = parseropts.child('Encoding').value()
            startByteStr = parseropts.child('StartByte').value()
            self.parameters['parser']['startbyte'] = list(bytearray.fromhex(startByteStr.replace(" ", "")))
            self.parameters['parser']['discardbytes'] = parseropts.child('DiscardBytes').value()
            endByteStr = parseropts.child('EndByte').value()
            self.parameters['parser']['endbyte'] = list(bytearray.fromhex(endByteStr.replace(" ", "")))
            numchan = parseropts.child('Channels').value()
            self.parameters['parser']['channel'] = numchan
            self.parameters['parser']['checksum'] = parseropts.child('CheckSum').value()
            self.parameters['parser']['datatype'] = parseropts.child('DataType').value()
            self.parameters['parser']['endianness'] = parseropts.child('Endianness').value()

            # add/remove channel entries in parameter tree
            channelopts = self.channels
            with channelopts.treeChangeBlocker():
                childcount = len(channelopts.children())
                if childcount == 0:
                    buttonDeselectAll = channelopts.addChild({'name': "Deselect All", 'type': 'action', 'visible': True})
                    buttonDeselectAll.sigActivated.connect(self.deselectAll)
                    buttonSelectAll = channelopts.addChild({'name': "Select All", 'type': 'action', 'visible': False})
                    buttonSelectAll.sigActivated.connect(self.selectAll)
                childcount = len(channelopts.children()) - 2

                for ch in range(max(numchan, childcount)):
                    chtitle = self.parameters['channel_config']["Channel_{}".format(ch)]['name']
                    chcolor = self.parameters['channel_config']["Channel_{}".format(ch)]['color']
                    if ch >= numchan:
                        channelopts.removeChild(channelopts.child(("Channel_{0}".format(ch))))
                    elif ch >= childcount:
                        child = channelopts.addChild({'name': "Channel_{}".format(ch), 'title': chtitle, 'type': 'bool', 'value': True})
                        chtitle = child.addChild({'name': 'Name', 'type': 'str', 'value': chtitle})
                        child.addChild({'name': 'Color', 'type': 'color', 'value': chcolor})
                        child.addChild({'name': 'Value', 'type': 'float', 'value': 0.0, 'readonly': True})
            dataitems_t = self.plotter_t.listDataItems()
            dataitems_f = self.plotter_f.listDataItems()
            numdataitems = len(dataitems_t)

            for ch in range(max(numchan, numdataitems)):
                if ch >= numchan:
                    self.plotter_t.removeItem(dataitems_t[ch])
                    self.plotter_f.removeItem(dataitems_f[ch])
                if len(self.chdata) <= ch:
                    self.chdata.append([])
                if ch >= numdataitems:
                    chtitle = self.parameters['channel_config']["Channel_{}".format(ch)]['name']
                    chcolor = self.parameters['channel_config']["Channel_{}".format(ch)]['color']
                    plotData = pg.PlotDataItem(pen=chcolor, name=chtitle)
                    self.plotter_t.addItem(plotData)
                    plotData = pg.PlotDataItem(pen=chcolor, name=chtitle)
                    self.plotter_f.addItem(plotData)

            # set new parser config
            self.parser.setParserScheme(aEncoding=self.parameters['parser']['encoding'],
                                        aStartSequence=self.parameters['parser']['startbyte'],
                                        aDiscardBytes=self.parameters['parser']['discardbytes'],
                                        aEndSequence=self.parameters['parser']['endbyte'],
                                        aCheckSum=self.parameters['parser']['checksum'],
                                        aDataType=self.parameters['parser']['datatype'],
                                        aNumChannel=self.parameters['parser']['channel'],
                                        aEndianness=self.parameters['parser']['endianness'])

            expectedStr = self.parser.getExpected()
            parseropts.child('Expected').setValue(expectedStr)

    def paramPlotterChanged(self):
        if self.debug:
            print("paramPlotterChanged")
        plotteropts = self.sources.child('plotopts').child('plotteropts')
        self.parameters['plotter']['autoscale'] = plotteropts.child('Autoscale').value()
        self.parameters['plotter']['buffersize'] = plotteropts.child('Plot Length').value()
        self.parameters['plotter']['offset'] = plotteropts.child('Offset').value()
        self.parameters['plotter']['multiplier'] = plotteropts.child('Multiplier').value()
        self.calculateXAxes()

    def paramFftChanged(self):
        if self.debug:
            print("paramFftChanged")
        fftopts = self.sources.child('plotopts').child('fftopts')
        self.parameters['fft']['enable'] = fftopts.child('Enable').value()
        self.parameters['fft']['autoscale'] = fftopts.child('Autoscale').value()
        self.parameters['fft']['showdc'] = fftopts.child('Show DC').value()
        self.parameters['fft']['fftsize'] = fftopts.child('NSamples').value()
        self.calculateXAxes()

    def serial_connect(self):
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
            self.statusBar().showMessage(msg)
            print(msg)
            return

        msg = "Connected to: {} ({})".format(portname, baudrate)
        self.statusBar().showMessage(msg)
        print(msg)

        gconnect = self.sources.child('connect')
        connectedstr = "{} :{}".format(portname, baudrate)
        gconnect.child('connected').setOpts(visible=True, value=connectedstr)
        gconnect.setOpts(title="Disconnect")
        gconnect.sigActivated.disconnect(self.serial_connect)
        gconnect.sigActivated.connect(self.serial_disconnect)
        self.sources.child('serialopts').hide()
        print(self.ser)

    def serial_disconnect(self):
        if self.debug:
            print("disconnect")
        self.ser.close()

        if self.ser.is_open == False:
            gconnect = self.sources.child('connect')
            gconnect.setOpts(title="Connect")
            gconnect.sigActivated.disconnect(self.serial_disconnect)
            gconnect.sigActivated.connect(self.serial_connect)
            self.sources.child('serialopts').show()
            self.sources.child('connect').child('connected').setOpts(visible=False)

            msg = "Disconnected"
            self.statusBar().showMessage(msg)
            print(msg)
        else:
            msg = "Unable to disconnect"
            self.statusBar().showMessage(msg)
            print(msg)

    def captureplot(self):
        exporter = pg.exporters.ImageExporter( self.glw.scene() )

        filename = 'IMAG_' + time.strftime('%Y%m%d_%H%M%S')
        exporter.export(filename + '.png')

        msg = 'Capture recorded as ' + filename + '.png'
        self.statusBar().showMessage(msg)
        print(msg)

    def update_plot(self):
        if self.ser == None:
            return

        data = bytes()

        if self.ser.is_open:
            try:
                inw = self.ser.in_waiting
                data = self.ser.read(inw)

            except:
                self.disconnect()
                print("Port disconnected...")
                return

        self.queue = len(data)

        self.dataBuffer = self.parser.parse(data)

        if len(self.dataBuffer) == 0:
            return

        if len(self.dataBuffer[0]) == 0:
            return

        # Apply multiplier and offset to the data
        multiplier = self.parameters['plotter']['multiplier']
        offset = self.parameters['plotter']['offset']
        for i, ch in enumerate(self.dataBuffer):
            for j, data in enumerate(ch):
                data *= multiplier
                data += offset
                self.dataBuffer[i][j] = data

        # Generate timestamps for the bulk-received packets
        currentTime = time.time()
        if self.lastPacketTime is None:
            # If no previous packet time, use current time for the entire buffer
            timestamps = [currentTime for _ in range(len(self.dataBuffer[0]))]
        else:
            # Distribute timestamps evenly between the last packet and now
            numPackets = len(self.dataBuffer[0])
            timeDiff = currentTime - self.lastPacketTime
            timestamps = [
                self.lastPacketTime + (timeDiff / numPackets) * i
                for i in range(numPackets)
            ]

        # Update the last packet time
        self.lastPacketTime = currentTime

        # update log file
        if self.startLogging:
            transposedBuffer = list(map(list, zip(*self.dataBuffer)))
            for i, data in enumerate(transposedBuffer):
                timestamp = timestamps[i] - self.logStartTime
                self.logfilehandle.write(f"{timestamp:.5f}, {', '.join(map(str, data))}\n")

        # Append the new data to the channel data
        numch = self.parameters['parser']['channel']
        for ch in range(numch):
            self.chdata[ch].extend(self.dataBuffer[ch])

        # draw time domain plot
        tstart = - min(self.parameters['plotter']['buffersize'] + 1, len(self.chdata[0]))
        tend = -1

        activechs = self.parameters['channels']['activechs']
        inactivechs = self.parameters['channels']['inactivechs']
        dataItems_t = self.plotter_t.listDataItems()

        for i, ch in enumerate(activechs):
            if i >= len(dataItems_t):
                continue

            if len(dataItems_t) > i:
                # prepend zeros if the data is shorter than the plot length
                lenChData = len(self.chdata[ch][tstart:tend])
                lenXt = len(self.Xt[0:-tstart-1])
                if lenChData != lenXt:
                    numZeros = lenXt - lenChData
                    self.chdata[ch][tstart:tend] = [0] * numZeros + self.chdata[ch][tstart:tend]

                # update plot data
                dataItems_t[i].setData(self.Xt[0:-tstart-1], self.chdata[ch][tstart:tend])

        # draw frequency domain plot
        if self.parameters['fft']['enable'] == False:
            self.glw.ci.layout.itemAt(1).setVisible(False)
        else:
            self.glw.ci.layout.itemAt(1).setVisible(True)
            lfNSamples = self.parameters['fft']['fftsize']
            if(len(self.chdata[0]) > lfNSamples):
                tstart = -min(lfNSamples + 1, len(self.chdata[0]))
                fstart = 1
                if self.parameters['fft']['showdc'] == True:
                    fstart = 0
                fend = (lfNSamples // 2) - 1

                dataItems_f = self.plotter_f.listDataItems()

                for i, ch in enumerate(activechs):
                    if i >= len(dataItems_f):
                        continue
                    if len(dataItems_t) > i:
                        self.Yf = fft(self.chdata[ch][tstart:tend])
                        dataItems_f[i].setData(self.Xf[fstart:fend], abs(self.Yf[fstart:fend]))

    def update_ui(self):
        self.counter += 1
        if self.parser == None:
            return

        self.labelpacketrate.setText("%d pps" % self.parser.getPacketRate())
        self.labelerrorrate.setText("%d pps" % self.parser.getErrorRate())
        self.labelpacketqueue.setText("Queue: %d pps" % self.queue)
        if self.startLogging:
            # blink the logging icon
            if self.counter % 2 == 0:
                self.labellogicon.setVisible(True)
            else:
                self.labellogicon.setVisible(False)
            self.labellog.setText("Logging: %s" % self.logfile)
        else:
            self.labellogicon.setVisible(False)
            self.labellog.setText("")

        # Update channel value
        if self.dataBuffer is not None:
            for i in range(self.parser.numChannels):
                if len(self.dataBuffer) <= i:
                    break
                if len(self.dataBuffer[i]) > 0:
                    self.channels.child("Channel_{0}".format(i)).child('Value').setValue(self.dataBuffer[i][-1])
        self.calculateXAxes()

def main():
    app = QApplication(sys.argv)
    window = SerialStudio(debug=False)
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
