import logging
import time
import serial.tools
import serial.tools.list_ports
import yaml
import serial
import argparse
import os
import glob
import threading
import paho.mqtt.client as mqtt
import sys

BANNER = r'''
  _____   ____   _____     _____ _   _ _______ ______ _____  ______      _____ ______  
 |  __ \ / __ \ / ____|   |_   _| \ | |__   __|  ____|  __ \|  ____/\   / ____|  ____| 
 | |__) | |  | | (___ ______| | |  \| |  | |  | |__  | |__) | |__ /  \ | |    | |__    
 |  ___/| |  | |\___ \______| | | . ` |  | |  |  __| |  _  /|  __/ /\ \| |    |  __|   
 | |    | |__| |____) |    _| |_| |\  |  | |  | |____| | \ \| | / ____ \ |____| |____  
 |_|     \____/|_____/    |_____|_| \_|  |_|  |______|_|  \_\_|/_/    \_\_____|______| 
                                                                                                                                                                              
'''

POS_CONFIG_FILE = "./config/pos_config.yaml"
PRINTER_CONFIG_FILE = "./config/printer_config.yaml"

BROKER_POS_INIT_STATUS_TOPIC = "pos/init"
BROKER_PRINTER_INIT_STATUS_TOPIC = "printer/init"
BROKER_SWITCH_INIT_STATUS_TOPIC = "switch/init"
BROKER_POS_BILL_STATUS_TOPIC = "pos/billing"
            
class POSInterface:
    def __init__(self, pos_config = POS_CONFIG_FILE, print_config = PRINTER_CONFIG_FILE):
        self._pos_config_file = pos_config
        self._print_config_file = print_config
        try:
            # Create an MQTT client instance
            self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)

            # Set the callback functions
            self._client.on_connect = self._on_connect
            self._client.on_message = self._on_message
        
            # Connect to the MQTT broker (localhost)
            self._client.connect("localhost", 1883, 60)

            # Start the MQTT network loop
            self._client.loop_start()
        except Exception as e:
            logging.error("Error in setting up local broker")
            raise
        ### POS setup    
        if not os.path.exists(self._pos_config_file):
            logging.error("POS config file not found")
            raise
        
        try:
            with open(self._pos_config_file, 'r') as f:
                self._pos_config = yaml.safe_load(f)
        except Exception as e:
            logging.error("Could not load YAML")
            raise e
        
        logging.debug("Loading POS config from file={}, service={}".format(self._pos_config_file, self._pos_config['service']))
        
        self._pos_serial_port = self._pos_config['SETTINGS']['SERIAL']['static_port']
        self._pos_baud_rate = self._pos_config['SETTINGS']['SERIAL']['baud']
        self._pos_serial_setting = self._pos_config['SETTINGS']['SERIAL']['serial_setting']

        self._pos_generic_strings = self._pos_config['GENERIC_STRINGS']
        self._pos_success_strings = self._pos_config['SUCCESS_STRINGS']
        self._pos_failure_strings = self._pos_config['FAILURE_STRINGS']
        
        logging.debug("Setting up POS serial interface")
        logging.debug("Attempting to connect to {} {} {}".format(self._pos_serial_port, self._pos_baud_rate, self._pos_serial_setting))
        try:
            self._pos_ser = serial.Serial(
            port=self._pos_serial_port,
            baudrate=int(self._pos_baud_rate),
            bytesize=int(self._pos_serial_setting[0]),
            parity=self._pos_serial_setting[1],
            stopbits=int(self._pos_serial_setting[2])
            )
            logging.info("Connected to POS serial port: {}".format(self._pos_serial_port))
            self._client.publish(BROKER_POS_INIT_STATUS_TOPIC, "True")
        except Exception as e:
            self._pos_ser = None
            logging.error("Error connecting to POS serial port:", e)
            self._client.publish(BROKER_POS_INIT_STATUS_TOPIC, "False")
            raise
        
        ### Printer setup
        try:
            with open(self._print_config_file, 'r') as f:
                self._print_config = yaml.safe_load(f)
        except Exception as e:
            logging.error("Could not load YAML")
            raise e
        
        logging.debug("Loading Printer config from file={}, service={}".format(self._print_config_file, self._print_config['service']))
        self._print_enabled = self._print_config['enabled']
        
        if self._print_enabled:
            self._print_serial_port = self._print_config['SETTINGS']['SERIAL']['static_port']
            self._print_baud_rate = self._print_config['SETTINGS']['SERIAL']['baud']
            self._print_serial_setting = self._print_config['SETTINGS']['SERIAL']['serial_setting']
            try:
                self._print_ser = serial.Serial(
                    port=self._print_serial_port,
                    baudrate=int(self._print_baud_rate),
                    bytesize=int(self._print_serial_setting[0]),
                    parity=self._print_serial_setting[1],
                    stopbits=int(self._print_serial_setting[2])
                )
                logging.info("Connected to Print serial port: {}".format(self._print_serial_port))
                self._client.publish(BROKER_PRINTER_INIT_STATUS_TOPIC, "True")
            except Exception as e:
                self._print_ser = None
                logging.error("Error connecting to Printer serial port: %s", e)
                self._client.publish(BROKER_PRINTER_INIT_STATUS_TOPIC, "False")
                raise
        else:
            logging.info("Printer interface not enabled, moving on!")

        if self._pos_ser is None:
            logging.error("POS serial port not found, starting thread to wait for it")
            exit_flag = True
            while exit_flag:
                ports = serial.tools.list_ports.comports()
                logging.info("Looking for port: {}".format(self._pos_serial_port))
                for port in ports:
                    logging.info(f"Device: {port.device}")
                    logging.info(f"Description: {port.description}")
                    logging.info(f"Hardware ID: {port.hwid}")
                    logging.info("-" * 20)
                    if port.device == self._pos_serial_port:
                        exit_flag = False
                time.sleep(5)
            try:
                self._pos_ser = serial.Serial(
                port=self._pos_serial_port,
                baudrate=int(self._pos_baud_rate),
                bytesize=int(self._pos_serial_setting[0]),
                parity=self._pos_serial_setting[1],
                stopbits=int(self._pos_serial_setting[2])
                )
                logging.info("Connected to POS serial port: {}".format(self._pos_serial_port))
                self._client.publish(BROKER_POS_INIT_STATUS_TOPIC, "True")
            except Exception as e:
                logging.error("Error connecting to POS serial port:", e)
                self._client.publish(BROKER_POS_INIT_STATUS_TOPIC, "False")
                raise

        if self._print_enabled and self._print_ser is None:
            logging.error("Printer serial port not found, starting thread to wait for it")
            exit_flag = True
            while exit_flag:
                ports = serial.tools.list_ports.comports()
                logging.info("Looking for port: {}".format(self._print_serial_port))
                for port in ports:
                    logging.info(f"Device: {port.device}")
                    logging.info(f"Description: {port.description}")
                    logging.info(f"Hardware ID: {port.hwid}")
                    logging.info("-" * 20)
                    if port.device == self._print_serial_port:
                        exit_flag = False
                time.sleep(5)
            try:
                self._print_ser = serial.Serial(
                    port=self._print_serial_port,
                    baudrate=int(self._print_baud_rate),
                    bytesize=int(self._print_serial_setting[0]),
                    parity=self._print_serial_setting[1],
                    stopbits=int(self._print_serial_setting[2])
                )
                logging.info("Connected to Printer serial port: {}".format(self._print_serial_port))
                self._client.publish(BROKER_PRINTER_INIT_STATUS_TOPIC, "True")
            except Exception as e:
                logging.error("Error connecting to Printer serial port:", e)
                self._client.publish(BROKER_PRINTER_INIT_STATUS_TOPIC, "False")
                self._print_enabled = False
        if self._print_enabled == False:
            logging.error("Printer setup failed")
            self._client.publish(BROKER_PRINTER_INIT_STATUS_TOPIC, "False")
        else:
            logging.info("Printer setup success")
            self._client.publish(BROKER_PRINTER_INIT_STATUS_TOPIC, "True")
    
    def _on_connect(self, client, userdata, flags, rc):
        logging.debug("Connected to message broker")
        self._client.subscribe(BROKER_SWITCH_INIT_STATUS_TOPIC)
        
    def _on_message(self, client, userdata, msg):
        logging.debug("Received message: {} {}".format(msg.topic, msg.payload.decode()))
        
    def cleanup(self):
        self._pos_ser.close()
        self._print_serial_port.close()
        self._client.disconnect()
        
    def run(self):
        logging.info("starting pos-printer state machine")
        err = 0
        while True:
            try:
                line = self._pos_ser.readline().decode('utf-8')
                err = 0
                logging.debug("Line received: {}".format(line))
                if any(string in line for string in self._pos_generic_strings):
                    # Only for debugging
                    logging.debug("Generic string found: {}".format(line))
                elif any(string in line for string in self._pos_success_strings):
                    logging.debug("Success string found:{}".format(line))
                    # Let the Switch know
                    self._client.publish(BROKER_POS_BILL_STATUS_TOPIC, "True")
                elif any(string in line for string in self._pos_failure_strings):
                    logging.debug("Failure string found:{}".format(line))
                    # Let the switch know
                    self._client.publish(BROKER_POS_BILL_STATUS_TOPIC, "False")

                # send to printer for print
                if self._print_enabled:
                    try:
                        # Open serial port and write to it
                        self._print_ser.write(line.encode())
                        logging.debug("Printing to printer: {}".format(line))
                    except Exception as e:
                        logging.error("Error printing from printer")
                        raise e
            except Exception as e:
                logging.error("Error reading from serial port:", e)
                logging.warning("Continuing to read from serial port")
                err += 1
            
            if err > 5:
                logging.error("Too many errors, exiting")
                break

        self._client.loop_stop()
        self._client.disconnect()        
        logging.info("Ending pos-printer state machine")

def print_banner():
    print(BANNER)

if __name__ == '__main__':
    # print_banner()
    parser = argparse.ArgumentParser(
                    prog='app.py',
                    description='Interface to the POS')

    parser.add_argument('--log-level', default="INFO", choices=set(["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]))
    parser.add_argument('--pos-port', default="/dev/ttyUSB0", help="POS serial port")
    parser.add_argument('--pos-baud', default=38400, help="POS serial baud rate")
    parser.add_argument('--print-port', default="/dev/ttyUSB1", help="Printer serial port")
    parser.add_argument('--print-baud', default=38400, help="Printer serial baud rate")
    
    args = parser.parse_args()
    logging.basicConfig(level=args.log_level, format='%(asctime)s %(message)s')
    
    # Open POS config and update static_port to POS_PORT
    with open(POS_CONFIG_FILE, 'r') as f:
        pos_config = yaml.safe_load(f)
        pos_config['SETTINGS']['SERIAL']['static_port'] = args.pos_port
        pos_config['SETTINGS']['SERIAL']['baud'] = args.pos_baud
    
    with open(PRINTER_CONFIG_FILE, 'r') as f:
        print_config = yaml.safe_load(f)
        print_config['SETTINGS']['SERIAL']['static_port'] = args.print_port
        print_config['SETTINGS']['SERIAL']['baud'] = args.print_baud
    
    logging.info("Starting POS interface")
    try:
        posif = POSInterface(pos_config=POS_CONFIG_FILE, print_config=PRINTER_CONFIG_FILE)
    except Exception as e:
        logging.error("Error initializing the POS interface, error = {}".format(e))
        time.sleep(5)
        sys.exit(1)
        
    try:
        posif.run()
    except Exception as e:
        posif.cleanup()
        logging.error("Error running the POS interface, error = {}".format(e))
