#!/bin/sh

echo "Setting up USB connection"
# Execute the modprobe command
modprobe -a dwc2 g_serial --first-time

if [ -c "/dev/ttyGS0" ]; then
  echo "modprobe command success, /dev/ttyGS0 exists"
else
  echo "modprobe failed"
fi

# Exit the container
exit 0