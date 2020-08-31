# ChangeFilamentEnder3v2 script - Change filament at a given height.
# This script is based on the PostProcessingPlugin scripts in Cura.
# https://github.com/Ultimaker/Cura/tree/master/plugins/PostProcessingPlugin/scripts
# https://marlinfw.org/docs/gcode/G000-G001.html

# Copyright (c) 2020 Mike Skutta
# The PostProcessingPlugin is released under the terms of the AGPLv3 or higher.

# history / change-log:
# V0.0.1 - Initial

from ..Script import Script

from UM.Application import Application #To get the current printer's settings.
from UM.Logger import Logger

from typing import List, Tuple

class ChangeFilamentEnder3v2(Script):
    version = "0.0.19"

    def __init__(self) -> None:
        super().__init__()

    def getSettingDataString(self) -> str:
        return """{
            "name": "Change Filament Ender 3 v2 (""" + self.version + """)",
            "key": "ChangeFilamentEnder3v2",
            "metadata": {},
            "version": 2,
            "settings":
            {
                "layer_number":
                {
                    "label": "Layer",
                    "description": "After what layer should filament change occur.",
                    "type": "int",
                    "default_value": 1,
                    "minimum_value": "0"
                },
                "head_park_x":
                {
                    "label": "Park Print Head X",
                    "description": "What X location does the head move to when pausing.",
                    "unit": "mm",
                    "type": "float",
                    "default_value": 245,
                    "minimum_value": "0"
                },
                "head_park_y":
                {
                    "label": "Park Print Head Y",
                    "description": "What Y location does the head move to when pausing.",
                    "unit": "mm",
                    "type": "float",
                    "default_value": 10,
                    "minimum_value": "0"
                },
                "head_park_z_min":
                {
                    "label": "Park Print Head Minimum Z",
                    "description": "What minimum Z location does the head move to when pausing.",
                    "unit": "mm",
                    "type": "float",
                    "default_value": 0,
                    "minimum_value": "0"
                },
                "disable_endstops":
                {
                    "label": "Disable Endstops",
                    "description": "Enable parking the print head outside of the build area. Be careful.",
                    "type": "bool",
                    "default_value": true
                },
                "minimize_backlash":
                {
                    "label": "Minimize Z Backlash",
                    "description": "Minimize Z backlash by dropping the Z-axis to the previous Z position and restoring to current Z. Park X/Y must be away from print to prevent damage.",
                    "type": "bool",
                    "default_value": false
                },
                "initial_retraction_amount":
                {
                    "label": "Initial Retraction",
                    "description": "Initial filament retraction distance. The filament will be retracted with this amount before moving the nozzle away from the ongoing print.",
                    "unit": "mm",
                    "type": "float",
                    "default_value": 5,
                    "minimum_value": "0"
                },
                "initial_retraction_speed":
                {
                    "label": "Initial Retraction Speed",
                    "description": "How fast to retract the filament.",
                    "unit": "mm/s",
                    "type": "float",
                    "default_value": 25,
                    "minimum_value": "0",
                    "enabled": false
                },
                "later_retraction_amount":
                {
                    "label": "Later Retraction Distance",
                    "description": "Later filament retraction distance for removal. The filament will be retracted all the way out of the printer so that you can change the filament.",
                    "unit": "mm",
                    "type": "float",
                    "default_value": 30.0,
                    "minimum_value": "0"
                },
                "later_retraction_speed":
                {
                    "label": "Later Retraction Speed",
                    "description": "How fast to retract the filament.",
                    "unit": "mm/s",
                    "type": "float",
                    "default_value": 25,
                    "minimum_value": "0",
                    "enabled": false
                },
                "auto_purge":
                {
                    "label": "Auto Purge",
                    "description": "Purge nozzle automatically with defined purge amount",
                    "type": "bool",
                    "default_value": true
                },
                "purge_amount":
                {
                    "label": " - Purge Distance",
                    "description": "Amount to purge after filament change",
                    "unit": "mm",
                    "type": "float",
                    "default_value": 50,
                    "minimum_value": "0",
                    "enabled": "auto_purge"
                },
                "purge_speed":
                {
                    "label": " - Purge Speed",
                    "description": "How fast to purge the filament.",
                    "unit": "mm/s",
                    "type": "float",
                    "default_value": 5,
                    "minimum_value": "0",
                    "enabled": "auto_purge"
                },
                "wipe_nozzle":
                {
                    "label": "Wipe Nozzle",
                    "description": "Wait for user to manually wipe the nozzle.",
                    "type": "bool",
                    "default_value": false
                }
            }
        }"""

    def execute(self, data: List[str]) -> List[str]:
        """Inserts the pause commands.
        :param data: List of layers.
        :return: New list of layers.
        """
        pause_layer = self.getSettingValueByKey("layer_number")
        park_x = self.getSettingValueByKey("head_park_x")
        park_y = self.getSettingValueByKey("head_park_y")
        park_z_min = self.getSettingValueByKey("head_park_z_min")
        disable_endstops = self.getSettingValueByKey("disable_endstops")
        minimize_backlash = self.getSettingValueByKey("minimize_backlash")
        initial_retraction_amount = self.getSettingValueByKey("initial_retraction_amount")
        initial_retraction_speed = self.getSettingValueByKey("initial_retraction_speed")
        later_retraction_amount = self.getSettingValueByKey("later_retraction_amount")
        later_retraction_speed = self.getSettingValueByKey("later_retraction_speed")
        auto_purge = self.getSettingValueByKey("auto_purge")
        purge_amount = self.getSettingValueByKey("purge_amount")
        purge_speed = self.getSettingValueByKey("purge_speed")
        wipe_nozzle = self.getSettingValueByKey("wipe_nozzle")
        layers_started = False
        max_x = Application.getInstance().getGlobalContainerStack().getProperty("machine_width", "value")
        max_y = Application.getInstance().getGlobalContainerStack().getProperty("machine_depth", "value")

        # Ensure park_x and park_y are in range. Pad with 10mm to prevent hitting end stops
        if not disable_endstops:
            if park_x < 10:
                park_x = 10
            if park_y < 10:
                park_y = 10
            if park_x > max_x - 10:
                park_x = max_x - 10
            if park_y > max_y - 10:
                park_y = max_y - 10

        current_x = 0
        current_y = 0
        current_z = 0
        current_layer = 0
        current_f = 0
        current_t = 0
        previous_z = 0

        nbr_negative_layers = 0

        for index, layer in enumerate(data):
            lines = layer.split("\n")

            # Scroll each line of instruction for each layer in the G-code
            for line in lines:
                # Fist positive layer reached
                if ";LAYER:0" in line:
                    layers_started = True
                # Count nbr of negative layers (raft)
                elif ";LAYER:-" in line:
                    nbr_negative_layers += 1

                #Track the latest printing temperature in order to resume at the correct temperature.
                m = self.getValue(line, "M")
                if m is not None and (m == 104 or m == 109) and self.getValue(line, "S") is not None:
                    current_t = self.getValue(line, "S")

                # Do not continue beyond this point until layers have started
                if not layers_started:
                    continue

                # Look for the feed rate of an extrusion instruction
                if self.getValue(line, "F") is not None and self.getValue(line, "E") is not None:
                    current_f = self.getValue(line, "F")

                # If an X instruction is in the line, read the current X
                if self.getValue(line, "X") is not None:
                    current_x = self.getValue(line, "X")

                # If a Y instruction is in the line, read the current Y
                if self.getValue(line, "Y") is not None:
                    current_y = self.getValue(line, "Y")

                # If a Z instruction is in the line, read the current Z. Keep previous Z.
                if self.getValue(line, "Z") is not None:
                    previous_z = current_z
                    current_z = self.getValue(line, "Z")

                # Pause at layer
                if not line.startswith(";LAYER:"):
                    continue
                current_layer = line[len(";LAYER:"):]
                try:
                    current_layer = int(current_layer)

                # Couldn't cast to int. Something is wrong with this
                # g-code data
                except ValueError:
                    continue
                if current_layer < pause_layer - nbr_negative_layers:
                    continue

                prev_layer = data[index - 1]
                prev_lines = prev_layer.split("\n")
                current_e = 0.

                # Access last layer, browse it backwards to find
                # last extruder absolute position
                for prevLine in reversed(prev_lines):
                    current_e = self.getValue(prevLine, "E", -1)
                    if current_e >= 0:
                        break

                prepend_gcode = ";TYPE:CUSTOM\n"
                prepend_gcode += ";added code by post processing\n"
                prepend_gcode += ";script: ChangeFilamentEnder3v2.py v" + self.version + "\n"
                prepend_gcode += ";current x: {x}\n".format(x = current_x)
                prepend_gcode += ";current y: {y}\n".format(y = current_y)
                prepend_gcode += ";current z: {z}\n".format(z = current_z)
                prepend_gcode += ";previous z: {z}\n".format(z = previous_z)
                prepend_gcode += ";current e: {e}\n".format(e = current_e)
                prepend_gcode += ";current t: {t}\n".format(t = current_t)
                prepend_gcode += ";current f: {f}\n".format(f = current_f)
                prepend_gcode += ";current layer: {layer}\n".format(layer = current_layer)

                # Retraction
                prepend_gcode += self.putValue(M = 83) + " ; switch to relative E values for any needed retraction\n"
                if initial_retraction_amount > 0:
                    prepend_gcode += self.putValue(G = 1, E = -initial_retraction_amount, F = initial_retraction_speed * 60) + " ; initial filament retract\n"

                # Park at x and y
                if disable_endstops:
                    prepend_gcode += self.putValue(M = 400) + " ; finish moves\n"
                    prepend_gcode += self.putValue(M = 211, S = 0) + " ; disable endstops\n"
                prepend_gcode += self.putValue(G = 1, X = park_x, Y = park_y, F = 9000) + " ; move head away\n"
                
                # Move to min z
                if park_z_min > 0 and current_z < park_z_min:
                    prepend_gcode += self.putValue(G = 1, Z = park_z_min, F = 300) + " ; too close to bed, move to minimum z\n"

                # Eject Filament
                if later_retraction_amount > 0:
                    prepend_gcode += self.putValue(G = 1, E = -later_retraction_amount, F = later_retraction_speed * 60) + " ; eject filament\n"

                # Set extruder standby temperature
                prepend_gcode += self.putValue(M = 104, S = 0) + " ; standby temperature\n"

                # Disable Extruder to allow manual feed
                prepend_gcode += self.putValue(M = 18) + " E ; disable extruder\n"

                # Notify User
                prepend_gcode += "M117 Change Filament\n"
                prepend_gcode += self.putValue(M = 400) + " ; finish moves\n"
                prepend_gcode += self.putValue(M = 300) + " ; beep\n"

                # Wait for user before continuing
                #prepend_gcode += self.putValue(M = 25) + " ; Wait for user\n"
                prepend_gcode += self.putValue(M = 0) + " Change Filament ; Wait for user\n"
                
                # Set extruder resume temperature
                prepend_gcode += "M117 Heating Extruder\n"
                prepend_gcode += self.putValue(M = 109, S = current_t) + " ; resume temperature\n"

                if not auto_purge or purge_amount == 0:
                    prepend_gcode += "M117 Purge Filament\n"
                    prepend_gcode += self.putValue(M = 400) + " ; finish moves\n"
                    prepend_gcode += self.putValue(M = 300) + " ; beep\n"

                    # Wait for user before continuing
                    #prepend_gcode += self.putValue(M = 25) + " ; Wait for user\n"
                    prepend_gcode += self.putValue(M = 0) + " Purge Filament ; Wait for user\n"
                
                # Enable Extruder
                prepend_gcode += self.putValue(M = 17) + " E ; enable extruder\n"
                prepend_gcode += self.putValue(G = 4, S = 1) + " ; wait\n"

                # Purge
                if auto_purge and purge_amount != 0:
                    prepend_gcode += self.putValue(G = 1, E = purge_amount, F = purge_speed * 60) + " ; auto purge filament\n"
                    prepend_gcode += self.putValue(G = 4, S = 10) + " ; releave pressure\n"

                # Push the filament back,
                # and retract again, the properly primes the nozzle
                # when changing filament.
                if initial_retraction_amount != 0:
                    prepend_gcode += self.putValue(G = 1, E = initial_retraction_amount, F = initial_retraction_speed * 60) + " ; Extrude filament (prime)\n"
                    prepend_gcode += self.putValue(G = 1, E = -initial_retraction_amount, F = initial_retraction_speed * 60) + " ; Retract filament (prime)\n"
                    if wipe_nozzle: 
                        prepend_gcode += "M117 Wipe Nozzle\n"
                        prepend_gcode += self.putValue(M = 400) + " ; finish moves\n"
                        prepend_gcode += self.putValue(M = 300) + " ; beep\n"
                        prepend_gcode += self.putValue(M = 0, S = 10) + " Wipe Nozzle ; Wait for user\n"

                # Restore z position
                if park_z_min > 0 and current_z < park_z_min:
                    prepend_gcode += self.putValue(G = 1, Z = current_z, F = 300) + " ; move z back to current position\n"

                if minimize_backlash:
                    prepend_gcode += self.putValue(G = 1, Z = previous_z, F = 300) + " ; drop to previous z (minimize backlash)\n"
                    prepend_gcode += self.putValue(G = 1, Z = current_z, F = 300) + " ; raise to current z (minimize backlash)\n"

                # Move the head back
                prepend_gcode += self.putValue(G = 1, X = current_x, Y = current_y, F = 9000) + " ; move back to x/y position\n"
                if disable_endstops:
                    prepend_gcode += self.putValue(M = 400) + " ; finish moves\n"
                    prepend_gcode += self.putValue(M = 211, S = 1) + " ; enable endstops\n"

                if initial_retraction_amount != 0:
                    prepend_gcode += self.putValue(G = 1, E = initial_retraction_amount, F = initial_retraction_speed * 60) + " ; Extrude filament\n"

                if current_f != 0:
                    prepend_gcode += self.putValue(G = 1, F = current_f) + " ; restore extrusion feedrate\n"
                else:
                    Logger.log("w", "No previous feedrate found in gcode, feedrate for next layer(s) might be incorrect")

                prepend_gcode += self.putValue(M = 82) + " ; switch back to absolute E values\n"

                # reset extrude value to pre pause value
                prepend_gcode += self.putValue(G = 92, E = current_e) + "\n"

                layer = prepend_gcode + layer

                # Override the data of this layer with the
                # modified data
                data[index] = layer
                return data
        return data