#!/usr/bin/env python3
import octoprint.plugin
import serial

class BedLevelingPlugin(octoprint.plugin.StartupPlugin):
 
    def on_after_startup(self):
        # Check if printer is currently printing
        printer_state = self._printer.get_current_data()
        if printer_state['state']['flags']['printing']:
            self._logger.warning("Printer is currently printing. Returning last calculated mesh variation.")
            last_mesh_variation = self._settings.get_float(["last_mesh_variation"], default=0.0)
            return last_mesh_variation
        
        # Open serial port to communicate with Marlin firmware
        try:
            ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
        except serial.SerialException:
            self._logger.error("Could not connect to printer via serial. Returning last calculated mesh variation.")
            last_mesh_variation = self._settings.get_float(["last_mesh_variation"], default=0.0)
            return last_mesh_variation
        
        # Send GCODE command to retrieve bilinear bed leveling data
        ser.write(b'M420 V\n')
        
        # Read response and parse the bilinear bed leveling data
        response = ser.readlines()
        lines = [line.strip() for line in response.split("\n")]
        mesh_data = []
        for line in lines[1:]:
            values = line.split()
            mesh_data.append([float(val) for val in values])
        
        if not mesh_data:
            self._logger.error("No bilinear bed leveling data found. Returning last calculated mesh variation.")
            last_mesh_variation = self._settings.get_float(["last_mesh_variation"], default=0.0)
            return last_mesh_variation
        
        # Calculate mesh variation and return result
        mesh_data_float = [float(point) for point in mesh_data]
        mesh_min = min(mesh_data_float)
        mesh_max = max(mesh_data_float)
        mesh_variation = mesh_max - mesh_min
        
        # Check if the mesh has changed since the last time the script was run
        last_mesh_min = self._settings.get_float(["last_mesh_min"])
        last_mesh_max = self._settings.get_float(["last_mesh_max"])
        last_mesh_variation = self._settings.get_float(["last_mesh_variation"], default=0.0)
        
        if last_mesh_min == mesh_min and last_mesh_max == mesh_max:
            self._logger.info("Bed mesh has not changed since last run. Returning last calculated mesh variation: %s" % last_mesh_variation)
            return last_mesh_variation
        
        self._settings.set_float(["last_mesh_min"], mesh_min)
        self._settings.set_float(["last_mesh_max"], mesh_max)
        self._settings.set_float(["last_mesh_variation"], mesh_variation)
        self._settings.save()
        
        self._logger.info("Bed mesh variation calculated: %s" % mesh_variation)
        return mesh_variation
