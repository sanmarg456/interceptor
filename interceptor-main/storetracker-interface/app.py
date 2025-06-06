import logging
import time
import serial.tools
import serial.tools.list_ports
import yaml
import serial
import argparse
import os
import socket
import paho.mqtt.client as mqtt

SWITCH_CONFIG_FILE = "./config/switch_config.yaml"
BROKER_POS_BILL_STATUS_TOPIC = "pos/billing"
BROKER_POS_INIT_STATUS_TOPIC = "pos/init"
BROKER_PRINTER_INIT_STATUS_TOPIC = "printer/init"
BROKER_SWITCH_INIT_STATUS_TOPIC = "switch/init"

class SwitchInterface:
    def __init__(self, switch_config = SWITCH_CONFIG_FILE, ip = None, port = None):
        if ip == None or port == None:
            raise Exception("IP and Port cannot be none")
        
        self._switch_config_file = switch_config
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
        if not os.path.exists(self._switch_config_file):
            logging.error("POS config file not found")
            raise
        
        try:
            with open(self._switch_config_file, 'r') as f:
                self._switch_config = yaml.safe_load(f)
        except Exception as e:
            logging.error("Could not load YAML")
            raise e
        
        logging.debug("Loading Switch config from file={}, service={}".format(self._switch_config_file, self._switch_config['service']))
        if self._switch_config['SETTINGS']['auto_scan']:
            logging.error("auto_scan is not implemented, use static IP")
            raise
        else:
            self._switch_ip_address = ip
            self._switch_ip_port = int(port)
            logging.info("Using static TCP address {}:{}".format(self._switch_ip_address, self._switch_ip_port))
        
        self._checkout_id = self._switch_config['SETTINGS']['checkout_id']
        self._enabled = self._check_port()
        
        if not self._enabled:
            self._client.publish(BROKER_SWITCH_INIT_STATUS_TOPIC, "False")
            logging.error("Error connecting to IP {}:{}".format(self._switch_ip_address, self._switch_ip_port))
            raise Exception("Error in connecting to TCP port")
        else:
            self._client.publish(BROKER_SWITCH_INIT_STATUS_TOPIC, "True")
        
            logging.info("Switch init successful, using store tracker on IP {}:{}".format(self._switch_ip_address, self._switch_ip_port))
            
        
    def _check_port(self):
        port_avail = False
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((self._switch_ip_address, self._switch_ip_port))
            port_avail = True
            logging.info("Port {} on {} is available.".format(self._switch_ip_address, self._switch_ip_port))
        except:
            logging.info("Port {} on {} is closed.".format(self._switch_ip_address, self._switch_ip_port))
            port_avail = False
        finally:
            s.close()
        return port_avail
    
    def _send_acc_command(self, acc_command):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.500)
                for retry in range(0,5):
                    logging.info("trying.. {} Sending ACC message to {}:{}".format(retry, self._switch_ip_address, self._switch_ip_port))
                    s.connect((self._switch_ip_address, self._switch_ip_port))
                    s.sendall(acc_command.encode())

                    # Receive reply
                    data = s.recv(1024)
                    if(data):
                        reply = data.decode()
                        logging.info("Received reply from storetracker {}".format(reply))
                        break
                    
                s.close()
                return reply

        except Exception as e:
            logging.error("Error sending ACC command to storetracker: {}".format(e))
            return None
    
    def _generate_acc_command(self, checkout_id):
        timestamp = time.strftime("%Y%m%d%H%M%S")
        acc_command = f"ACC {timestamp}{checkout_id:04d}\n"
        return acc_command
    
    def _on_connect(self, client, userdata, flags, rc):
        logging.debug("Connected to message broker")
        self._client.subscribe(BROKER_POS_INIT_STATUS_TOPIC)
        self._client.subscribe(BROKER_PRINTER_INIT_STATUS_TOPIC)
        self._client.subscribe(BROKER_POS_BILL_STATUS_TOPIC)
        
    def _on_message(self, client, userdata, msg):
        logging.debug("Received message: {} {}".format(msg.topic, msg.payload.decode()))
        if msg.topic == BROKER_POS_BILL_STATUS_TOPIC:
            if msg.payload.decode() == "True":
                acc_command = self._generate_acc_command(self._checkout_id)
                logging.info("Sending ACC command: {}".format(acc_command))
                try:
                    self._send_acc_command(acc_command)
                except Exception as e:
                    logging.error("Error sending ACC command")
            elif msg.payload.decode() == "False":
                logging.info("Received a failed billing")
            else:
                logging.error("Unknown message on topic: {} = {}".format(msg.topic, msg.payload.decode()))

    def run(self):
        logging.info("starting storetracker state machine")
        while True:
            time.sleep(1)
        
        logging.info("Ending storetracker state machine")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
                    prog='app.py',
                    description='Interface to the storetracker')

    parser.add_argument('--log-level', default="INFO", choices=set(["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]))
    parser.add_argument('--switch-ip', default="192.168.0.2", help="Storetracker switch IP")
    parser.add_argument('--switch-port', default=25803, help="Storetracker switch port")
    
    args = parser.parse_args()
    logging.basicConfig(level=args.log_level, format='%(asctime)s %(message)s')
    
    logging.info("Starting Switch interface")
    try:
        storetracker = SwitchInterface(switch_config=SWITCH_CONFIG_FILE, ip=args.switch_ip, port=int(args.switch_port))
    except Exception as e:
        logging.error("Error initializing the Switch interface, error = {}".format(e))
        exit(-1)
        
    try:
        storetracker.run()
    except Exception as e:
        logging.error("Error running the Switch interface, error = {}".format(e))
        
    logging.error("program closing due to an error")
