#!/bin/sh

# defines
CONFIG_PATH="./config/"
DEVICE_NAME_FILE="/data/device_name.txt"
VENV_PYTHON=/opt/venv/bin/python3
LOGFILE_PATH="/data/storetracker.log"
args=""

# device name
if [ -f "$DEVICE_NAME_FILE" ]; then
    DEVICE_NAME=$(cat $DEVICE_NAME_FILE)
    echo "Device name file exists"
    export DEVICE_NAME
else
    echo "WARNING! Device name could not be found at $DEVICE_NAME_FILE. Will wait to get from Balena"
    # its always good to sleep and let container settle
    sleep 10

    while [ -z "$BALENA_DEVICE_NAME_AT_INIT" ]
    do
        sleep 2
        echo ">>>>>>> ERROR, could not get BALENA_DEVICE_NAME_AT_INIT. Waiting to try again"
    done
    DEVICE_NAME=$BALENA_DEVICE_NAME_AT_INIT
    echo "Successfully aquired Balena device name from Balena: $DEVICE_NAME"
    echo "$DEVICE_NAME" > "$DEVICE_NAME_FILE"
    export DEVICE_NAME
fi

# helper function for getting environment variables
register_arg() {
    local arg_name="$1"
    local arg_value="$2"

    if [ ! -z "$arg_value" ]; then
        args="$args $arg_name=$arg_value"
    fi
}

register_arg "--log-level" "$LOG_LEVEL"
register_arg "--switch-ip" "$SWITCH_IP"
register_arg "--switch-port" "$SWITCH_PORT"

echo "Launching with following commands"
echo $args | tee -a $LOGFILE_PATH

# start the python code
$VENV_PYTHON app.py $args > $LOGFILE_PATH 2>&1 &

APP_PID=$(pidof python3)
echo "App PID: $APP_PID"

if [ ! -d /proc/$APP_PID ]; then
    echo "Failed to start the app: $APP_PID"
    exit $APP_PID
fi

echo "App started!!!"

trap "echo 'Passing SIGTERM to PID: $APP_PID'; kill -15 $APP_PID" TERM
trap "echo 'Passing SIGTERM to PID: $APP_PID'; kill -2 $APP_PID" TERM
trap "echo 'Got exit, exiting'; exit" EXIT

# Monitor
while sleep 60; do
    if [ ! -d /proc/$APP_PID ]; then
        echo "storetracker app container died. Exiting"
        exit 1
    fi
done
