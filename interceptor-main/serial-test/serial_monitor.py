import serial
import logging

# Open connections to both serial ports
ser1 = serial.Serial('/dev/ttyUSB0', 38400, timeout=1)
ser2 = serial.Serial('/dev/ttyUSB1', 38400, timeout=1)

logging.info("Monitoring Serial Ports...")

while True:
    if ser1.in_waiting:
        logging.info("POS {}".format(ser1.readline().decode().strip()))

    # This should ideally not print anything
    if ser2.in_waiting:
        logging.info("Printer {}".format(ser2.readline().decode().strip()))
