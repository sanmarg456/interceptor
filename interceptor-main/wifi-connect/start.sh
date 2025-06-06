#!/usr/bin/env bash

# Script referenced from Balena example project: https://github.com/balena-io/wifi-connect/blob/master/scripts/start.sh
# Sometimes device can take a few seconds to establish WiFi connection,
# so wait to see if connection can be establish before checking internet connectivy.
sleep 15

# if WIFI_SSID_NAME exists, use it
# else if we have Balena name, use it
# otherwise use the hardcoded fallback name
if [ -n "$WIFI_SSID_NAME" ]; then
  SSID="$WIFI_SSID_NAME"
elif [ -n "$BALENA_DEVICE_NAME_AT_INIT" ]; then
  SSID="$BALENA_DEVICE_NAME_AT_INIT"
else
  SSID="WiFi_Connect"
fi

# Is there Internet connectivity via a google ping?
wget --spider http://google.com 2>&1

if [ $? -eq 0 ]; then
  printf "Skipping WiFi Connect\n"
else
  printf "Starting WiFi Connect with SSID: $SSID\n"
  ./wifi-connect --ui-directory /usr/src/app/custom_ui --portal-ssid $SSID
fi

# Sleep forever. If WiFi Connect needs to be relaunched, restart the device.
sleep infinity
