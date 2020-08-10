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
    version = "0.0.8"

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
                    "default_value": 10,
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
                    "default_value": 300.0,
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
                }
            }
        }"""

    def execute(self, data: List[str]) -> List[str]:
        """Inserts the pause commands.
        :param data: List of layers.
        :return: New list of layers.
        """
        pause_layer = self.getSettingValueByKey("layer_number")
        initial_retraction_amount = self.getSettingValueByKey("initial_retraction_amount")
        initial_retraction_speed = self.getSettingValueByKey("initial_retraction_speed")
        later_retraction_amount = self.getSettingValueByKey("later_retraction_amount")
        later_retraction_speed = self.getSettingValueByKey("later_retraction_speed")
        park_x = self.getSettingValueByKey("head_park_x")
        park_y = self.getSettingValueByKey("head_park_y")
        layers_started = False
        max_x = Application.getInstance().getGlobalContainerStack().getProperty("machine_width", "value")
        max_y = Application.getInstance().getGlobalContainerStack().getProperty("machine_depth", "value")

        # Ensure park_x and park_y are in range. Pad with 10mm to prevent hitting end stops
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

                # If a Z instruction is in the line, read the current Z
                if self.getValue(line, "Z") is not None:
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
                prepend_gcode += ";script: ChangeFilamentEnder3v2.py\n"
                prepend_gcode += ";current x: {x}\n".format(x = current_x)
                prepend_gcode += ";current y: {y}\n".format(y = current_y)
                prepend_gcode += ";current z: {z}\n".format(z = current_z)
                prepend_gcode += ";current e: {e}\n".format(e = current_e)
                prepend_gcode += ";current t: {t}\n".format(t = current_t)
                prepend_gcode += ";current f: {f}\n".format(f = current_f)
                prepend_gcode += ";current layer: {layer}\n".format(layer = current_layer)

                # Retraction
                prepend_gcode += self.putValue(M = 83) + " ; switch to relative E values for any needed retraction\n"
                if initial_retraction_amount > 0:
                    prepend_gcode += self.putValue(G = 1, E = -initial_retraction_amount, F = initial_retraction_speed * 60) + " ; initial filament retract\n"

                # Park at x and y
                prepend_gcode += self.putValue(G = 1, X = park_x, Y = park_y, F = 9000) + " ; move head away\n"

                # Eject Filament
                if later_retraction_amount > 0:
                    prepend_gcode += self.putValue(G = 1, E = -later_retraction_amount, F = later_retraction_speed * 60) + " ; eject filament\n"

                # Set extruder standby temperature
                prepend_gcode += self.putValue(M = 104, S = 0) + " ; standby temperature\n"

                # Disable Extruder to allow manual feed
                prepend_gcode += self.putValue(M = 18) + " E ; disable extruder\n"

                # Notify User
                prepend_gcode += "M117 Remove Filament\n"
                prepend_gcode += self.putValue(M = 400) + " ; Wait for buffer to clear\n"
                prepend_gcode += self.putValue(M = 300) + " ; beep\n"

                # Wait for user before continuing
                prepend_gcode += self.putValue(M = 25) + " ; Wait for user\n"
                
                # Set extruder resume temperature
                prepend_gcode += "M117 Heating Extruder\n"
                prepend_gcode += self.putValue(M = 109, S = current_t) + " ; resume temperature\n"

                prepend_gcode += "M117 Load Filament\n"
                prepend_gcode += self.putValue(M = 400) + " ; Wait for buffer to clear\n"
                prepend_gcode += self.putValue(M = 300) + " ; beep\n"

                # Wait for user before continuing
                prepend_gcode += self.putValue(M = 25) + " ; Wait for user\n"
                
                # Enable Extruder
                prepend_gcode += self.putValue(M = 17) + " E ; enable extruder\n"

                # Push the filament back,
                if initial_retraction_amount != 0:
                    prepend_gcode += self.putValue(G = 1, E = initial_retraction_amount, F = initial_retraction_speed * 60) + " ; Extrude filament\n"

                # and retract again, the properly primes the nozzle
                # when changing filament.
                if initial_retraction_amount != 0:
                    prepend_gcode += self.putValue(G = 1, E = -initial_retraction_amount, F = initial_retraction_speed * 60) + " : Retract filament\n"

                # Move the head back
                prepend_gcode += self.putValue(G = 1, X = current_x, Y = current_y, F = 9000) + " ; move back to x/y position\n"
                
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