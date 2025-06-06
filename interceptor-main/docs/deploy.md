To deploy a docker image onto a device follow the steps below.
1. From [Dashboard](https://dashboard.balena-cloud.com/) follow to the fleet and device.
2. Put the device into `local` mode by going into `Settings` menu. Note IP address of this device.
3. On your host machine, open project `interceptor` in VSCode.
4. On top, look for a bar tab, `Terminal`, open a new terminal.
5. In local mode, you'll need your RPi4 and host machine to be on the same network/WiFi.
6. Use command line tool to push onto the device as `balena push <IP_ADDR>`. This will initiate the build and push onto device. Wait for the message, "Device is settled"
7. To ssh onto a container/see logs, open another command line window in VSCode and run command
   ``` bash
   balena device ssh <IP_ADDR>
   tail -f /data/xyz.log
   ```

   For getting into a specific container, you can use
   
   ``` bash
   balena device ssh <IP_ADDR> <container_name>
   tail -f /data/xyz.log
   ```
   
   The above should open log file and show live logs.

To deploy releases, use following
1. On your host machine, open project `interceptor` in VSCode.
2. Open a terminal in VSCode.
3. Run the following to deploy a release to be used by one or all devices in the fleet,
   ``` bash
   balena login
   ```
   Follow steps for authentication using CLI
   ``` bash
   balena push <fleet_name>
   ```
4. Follow on [dashboard](https://dashboard.balena-cloud.com/) to see live updates on the release.
