# dbus-idm
IDM heat pump integration for Victron Venus OS

## Purpose
This script supports reading values from heat pumps produced by IDM via Modbus.
Currently supported are: flow temperature, power consumption, power factor, total energy.

Writing values is not supported right now.

## Installation & Configuration
### Download the latest version of the code
Grab a copy of the main branch and copy it to `/data/dbus-idm`.

```
wget https://github.com/fetsnleds/dbus-idm/archive/refs/heads/main.zip
unzip main.zip "dbus-idm-main/*" -d /data
mv /data/dbus-idm-main /data/dbus-idm
```
### Change the configuration file
Change the configuration file `/data/dbus-idm/config.ini` to fit your setup. The following table lists all available options.

| Section  | Config vlaue | Explanation |
| ------------- | ------------- | ------------- |
| DEFAULT  | SignOfLifeLog  | Time in minutes how often a status is written to the logfile `current.log` |
| DEFAULT  | Deviceinstance | Unique ID identifying the heat pump in Venus OS |
| DEFAULT  | Host | IP address or hostname of the heat pump |
| DEFAULT  | Port | Port (default: 502) |
| DEFAULT  | Position | 0: AC Out, 1: AC In (default: 0) |
| DEFAULT  | Model | Type of heat pump (e.g. ALM) |
| DEFAULT  | Timeout | Time in milliseconds how often the values should be read and updated |

### Install and run the service
Make the install script executable and run it. Clean up afterwards.

```
chmod a+x /data/dbus-idm/install.sh
mount -o remount,rw /
/data/dbus-idm/install.sh
rm main.zip
```

## Acknowledgements

* [dbusdummyservice](https://github.com/victronenergy/velib_python/blob/master/dbusdummyservice.py)
* [dbus-modbus-client](https://github.com/victronenergy/dbus-modbus-client)
* [dbus-lambda](https://codeberg.org/andreas-bulling/dbus-lambda)
