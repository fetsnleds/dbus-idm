#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
SERVICE_NAME=$(basename $SCRIPT_DIR)
RC_LOCAL_FILE=/data/rc.local

#remove the service
if [ -d /service/$SERVICE_NAME ]; then  
    rm /service/$SERVICE_NAME
fi 

# end the dbus-idm process
kill $(pgrep -f 'supervise dbus-idm')

# delete old logs if they exist  
if [ -f $SCRIPT_DIR/current.log ]; then  
    rm $SCRIPT_DIR/current.log*  
fi 

# remove install.sh from rc.local
STARTUP=$SCRIPT_DIR/install.sh
sed -i "\~$STARTUP~d" $RC_LOCAL_FILE
