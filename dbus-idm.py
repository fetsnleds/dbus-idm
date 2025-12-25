#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#  Please note that any incorrect or careless usage of this module as
#  well as errors in the implementation can damage your hardware!
#  Therefore, the author does not provide any guarantee or warranty
#  concerning to correctness, functionality or performance and does not
#  accept any liability for damage caused by this module, examples or
#  mentioned information.
#
#  Thus, use it at your own risk!

# import normal packages
import logging
import platform
import logging
import sys
import os
import time
import configparser # for config/ini file
import struct
from gi.repository import GLib as gobject

sys.path.insert(1, os.path.join(os.path.dirname(__file__), '/opt/victronenergy/dbus-systemcalc-py/ext/velib_python'))
from vedbus import VeDbusService

from pymodbus.client.sync import ModbusTcpClient
from pymodbus.exceptions import ModbusException

class DbusIDMService:
    def __init__(self, servicename, paths, productname='idm', connection='IDM Modbus Service'):
        config = self._getConfig()
        deviceinstance = int(config['DEFAULT']['Deviceinstance'])
        self.host = str(config['DEFAULT']['Host'])
        self.port = int(config['DEFAULT']['Port'])
        self.acposition = int(config['DEFAULT']['Position'])
        self.model = str(config['DEFAULT']['Model'])
        self.timeout = int(config['DEFAULT']['Timeout'])
        
        self._dbusservice = VeDbusService(servicename, register=False)
        self._paths = paths

        logging.debug("%s /DeviceInstance = %d" % (servicename, deviceinstance))

        # Create the management objects, as specified in the ccgx dbus-api document
        self._dbusservice.add_path('/Mgmt/ProcessName', __file__)
        self._dbusservice.add_path('/Mgmt/ProcessVersion', 'Unknown version, running on Python ' + platform.python_version())
        self._dbusservice.add_path('/Mgmt/Connection', connection)

        # Create the mandatory objects
        self._dbusservice.add_path('/DeviceInstance', deviceinstance)
        self._dbusservice.add_path('/ProductId', 0xFFFF)
        self._dbusservice.add_path('/ProductName', "IDM " + self.model)
        self._dbusservice.add_path('/CustomName', "IDM " + self.model)
        self._dbusservice.add_path('/FirmwareVersion', "0")
        self._dbusservice.add_path('/Serial', "0")
        self._dbusservice.add_path('/HardwareVersion', self.model)
        self._dbusservice.add_path('/Connected', 1)
        self._dbusservice.add_path('/UpdateIndex', 0)
        self._dbusservice.add_path('/Position', self.acposition) # 0: ac out, 1: ac in

        # add path values to dbus
        for path, settings in self._paths.items():
            self._dbusservice.add_path(path, settings['initial'], gettextcallback=settings['textformat'], writeable=True, onchangecallback=self._handlechangedvalue)

        # last update
        self._lastUpdate = 0

        self._dbusservice.register()

        # add _update function 'timer'
        gobject.timeout_add(self.timeout, self._update) # pause before the next request

        # add _signOfLife 'timer' to get feedback in log every x minutes
        gobject.timeout_add(self._getSignOfLifeInterval()*60*1000, self._signOfLife)

        # open Modbus connection to heatpump
        self._client = ModbusTcpClient(self.host, port=self.port)
        self._client.connect()
        logging.info("Modbus connected")

    def __del__(self):
        # close Modbus connection
        self._client.close()

    def _getConfig(self):
        config = configparser.ConfigParser()
        config.read("%s/config.ini" % (os.path.dirname(os.path.realpath(__file__))))
        return config
    
    def _getSignOfLifeInterval(self):
        config = self._getConfig()
        value = config['DEFAULT']['SignOfLifeLog']

        if not value:
            value = 0

        return int(value)
    
    def _handlechangedvalue(self, path, value):
        logging.critical("Someone else updated %s to %s" % (path, value))
        # TODO: handle changes

    def getIDMf32s(self, addr):
        try:
            result = self._client.read_input_registers(addr, count=2, unit=1)
        except ModbusException as exc:
            logging.error(f"Modbus exception: {exc!s}")
        if result.isError():
            print("Error:", result)
        payload = struct.pack("<2H", result.registers[0], result.registers[1])
        value = struct.unpack('<f', payload)[0]
        logging.debug(f"{addr}: {value}")
        return value
   
    def _signOfLife(self):
        logging.info("--- Start: sign of life ---")
        logging.info("Last _update() call: %s" % (self._lastUpdate))
        logging.info("Last '/Ac/Power': %s" % (self._dbusservice['/Ac/Power']))
        logging.info("--- End: sign of life ---")
        return True

    def _update(self):
        try:
            T_aussen_C = self.getIDMf32s(1000)
            T_speicher_C = self.getIDMf32s(1008)
            T_vorlaufA_C = self.getIDMf32s(1350)
            T_vorlaufAsoll_C = self.getIDMf32s(1378)
            E_heizen_kWh = self.getIDMf32s(1750)
            E_warmwasser_kWh = self.getIDMf32s(1754)
            P_mom_kW = self.getIDMf32s(1790)
            P_in_kW = self.getIDMf32s(4122)
            self._dbusservice['/State'] = 1
            self._dbusservice['/Temperature'] = T_vorlaufA_C
            self._dbusservice['/TargetTemperature'] = T_vorlaufAsoll_C
            self._dbusservice['/Ac/Power'] = P_in_kW
            self._dbusservice['/HeatOutput'] = P_mom_kW
            self._dbusservice['/Ac/Energy/Forward'] = E_heizen_kWh + E_warmwasser_kWh
            self._dbusservice['/PowerFactor'] = P_mom_kW/P_in_kW if P_in_kW > 0 else 0
            self._dbusservice['/AirTemperature'] = T_aussen_C

            # logging
            logging.debug("Operating State (/State): %s" % (self._dbusservice['/State']))
            logging.debug("Flow Temperature (/Temperature): %s" % (self._dbusservice['/Temperature']))
            logging.debug("Request Flow Temperature (/TargetTemperature): %s" % (self._dbusservice['/TargetTemperature']))
            logging.debug("Power Consumption (/Ac/Power): %s" % (self._dbusservice['/Ac/Power']))
            logging.debug("Total Energy (/Ac/Energy/Forward): %s" % (self._dbusservice['/Ac/Energy/Forward']))
            logging.debug("---")

            # increment UpdateIndex - to show that new data is available
            index = self._dbusservice['/UpdateIndex'] + 1  # increment index
            if index > 255:   # maximum value of the index
                index = 0       # overflow from 255 to 0
            self._dbusservice['/UpdateIndex'] = index

            # update lastupdate vars
            self._lastUpdate = time.time()

        except Exception as e:
            logging.critical('Error at %s', '_update', exc_info=e)
            logging.critical(e)

        # return true, otherwise add_timeout will be removed from GObject - see docs http://library.isr.ist.utl.pt/docs/pygtk2reference/gobject-functions.html#function-gobject--timeout-add
        return True


def main():
    # configure logging
    logging.basicConfig(  format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                          datefmt='%Y-%m-%d %H:%M:%S',
                          level=logging.INFO,
                          handlers=[
                              logging.FileHandler("%s/current.log" % (os.path.dirname(os.path.realpath(__file__)))),
                              logging.StreamHandler()
                          ]
                        )

    try:
        logging.info("Start")

        from dbus.mainloop.glib import DBusGMainLoop
        # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
        DBusGMainLoop(set_as_default=True)

        # formatting
        _kWh = lambda p, v: (str(round(v, 2)) + 'kWh')
        _a = lambda p, v: (str(round(v, 1)) + 'A')
        _w = lambda p, v: (str(round(v, 1)) + 'W')
        _v = lambda p, v: (str(round(v, 1)) + 'V')
        _degC = lambda p, v: (str(v) + '°C')
        _s = lambda p, v: (str(v) + 's')
        _n = lambda p, v: (str(v))

        # start our main-service
        hp_output = DbusIDMService(
          servicename='com.victronenergy.heatpump.idm',
          paths={
            '/State': {'initial': 0, 'textformat': _n},
            '/Temperature': {'initial': 0, 'textformat': _degC},
            '/TargetTemperature': {'initial': 0, 'textformat': _degC},
            '/AirTemperature': {'initial': 0, 'textformat': _degC},
            '/Ac/Power': {'initial': 0, 'textformat': _w},
            '/HeatOutput': {'initial': 0, 'textformat': _w},
            '/PowerFactor': {'initial': 0, 'textformat': _n},
            '/Ac/Energy/Forward': {'initial': 0, 'textformat': _kWh},
          }
        )

        logging.info('Connected to dbus and switching over to gobject.MainLoop() (= event based)')
        mainloop = gobject.MainLoop()
        mainloop.run()
    except Exception as e:
        logging.critical('Error at %s', 'main', exc_info=e)

if __name__ == "__main__":
    main()

