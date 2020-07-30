# ChangeFilamentEnder3v2 script - Change filament at a given height.
# This script is based on the PostProcessingPlugin scripts in Cura.
# https://github.com/Ultimaker/Cura/tree/master/plugins/PostProcessingPlugin/scripts

# Copyright (c) 2020 Mike Skutta
# The PostProcessingPlugin is released under the terms of the AGPLv3 or higher.

# history / change-log:
# V0.0.1 - Initial

from ..Script import Script

from UM.Application import Application #To get the current printer's settings.
from UM.Logger import Logger

from typing import List, Tuple

class ChangeFilamentEnder3v2(Script):
    version = "0.0.1"

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
                "initial_retraction_amount":
                {
                    "label": "Initial Retraction",
                    "description": "Initial filament retraction distance. The filament will be retracted with this amount before moving the nozzle away from the ongoing print.",
                    "unit": "mm",
                    "type": "float",
                    "default_value": 2,
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
                },
                "disarm_timeout":
                {
                    "label": "Disarm timeout",
                    "description": "After this time steppers are going to disarm (meaning that they can easily lose their positions). Set this to 0 if you don't want to set any duration.",
                    "type": "int",
                    "value": "0",
                    "minimum_value": "0",
                    "minimum_value_warning": "0",
                    "maximum_value_warning": "1800",
                    "unit": "s",
                    "enabled": false
                },
                "standby_temperature":
                {
                    "label": "Standby Temperature",
                    "description": "Change the temperature during the pause.",
                    "unit": "°C",
                    "type": "int",
                    "default_value": 0,
                    "minimum_value": "0"
                }
            }
        }"""

    ##  Get the X and Y values for a layer (will be used to get X and Y of the
    #   layer after the pause).
    def getNextXY(self, layer: str) -> Tuple[float, float]:
        """Get the X and Y values for a layer (will be used to get X and Y of the layer after the pause)."""
        lines = layer.split("\n")
        for line in lines:
            if line.startswith(("G0", "G1", "G2", "G3")):
                if self.getValue(line, "X") is not None and self.getValue(line, "Y") is not None:
                    x = self.getValue(line, "X")
                    y = self.getValue(line, "Y")
                    return x, y
        return 0, 0

    def execute(self, data: List[str]) -> List[str]:
        """Inserts the pause commands.
        :param data: List of layers.
        :return: New list of layers.
        """
        pause_layer = self.getSettingValueByKey("layer_number")
        disarm_timeout = self.getSettingValueByKey("disarm_timeout")
        initial_retraction_amount = self.getSettingValueByKey("initial_retraction_amount")
        initial_retraction_speed = self.getSettingValueByKey("initial_retraction_speed")
        later_retraction_amount = self.getSettingValueByKey("later_retraction_amount")
        later_retraction_speed = self.getSettingValueByKey("later_retraction_speed")
        park_x = self.getSettingValueByKey("head_park_x")
        park_y = self.getSettingValueByKey("head_park_y")
        layers_started = False
        standby_temperature = self.getSettingValueByKey("standby_temperature")
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

        current_z = 0
        current_layer = 0
        current_extrusion_f = 0
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
                    current_extrusion_f = self.getValue(line, "F")

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

                # Get X and Y from the next layer (better position for
                # the nozzle)
                next_layer = data[index + 1]
                x, y = self.getNextXY(next_layer)

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
                prepend_gcode += ";next x: {x}\n".format(x = x)
                prepend_gcode += ";next y: {y}\n".format(y = y)
                prepend_gcode += ";current z: {z}\n".format(z = current_z)
                prepend_gcode += ";current e: {e}\n".format(e = current_e)
                prepend_gcode += ";current t: {t}\n".format(t = current_t)
                prepend_gcode += ";current f: {f}\n".format(f = current_extrusion_f)
                prepend_gcode += ";current layer: {layer}\n".format(layer = current_layer)

                # Retraction
                prepend_gcode += self.putValue(M = 83) + " ; switch to relative E values for any needed retraction\n"
                if initial_retraction_amount > 0:
                    prepend_gcode += self.putValue(G = 1, E = -initial_retraction_amount, F = initial_retraction_speed * 60) + " ; initial filament retract\n"

                # Move the head away
                prepend_gcode += self.putValue(G = 1, Z = current_z + 1, F = 300) + " ; move up a millimeter to get out of the way\n"

                # Park at x and y
                prepend_gcode += self.putValue(G = 1, X = park_x, Y = park_y, F = 9000) + " ; move head away\n"

                if current_z < 15:
                        prepend_gcode += self.putValue(G = 1, Z = 15, F = 300) + " ; too close to bed--move to at least 15mm\n"

                # Eject Filament
                if later_retraction_amount > 0:
                    prepend_gcode += self.putValue(G = 1, E = -later_retraction_amount, F = later_retraction_speed * 60) + " ; eject filament\n"

                # Set extruder standby temperature
                prepend_gcode += self.putValue(M = 104, S = standby_temperature) + " ; standby temperature\n"

                prepend_gcode += "M117 Remove Filament\n"
                prepend_gcode += self.putValue(M = 400) + " ; Finish Moves\n"
                prepend_gcode += self.putValue(M = 300) + " ; beep\n"

                # Set the disarm timeout
                if disarm_timeout > 0:
                    prepend_gcode += self.putValue(M = 18, S = disarm_timeout) + " ; Set the disarm timeout\n"

                # Wait for user before continuing
                prepend_gcode += self.putValue(M = 25) + " ; Wait for user\n"

                # Set extruder resume temperature
                prepend_gcode += self.putValue(M = 109, S = current_t) + " ; resume temperature\n"

                prepend_gcode += "M117 Load Filament\n"
                prepend_gcode += self.putValue(M = 400) + " ; Wait for temperature\n"
                prepend_gcode += self.putValue(M = 300) + " ; beep\n"

                # Wait for user before continuing
                prepend_gcode += self.putValue(M = 25) + " ; Wait for user\n"

                # Push the filament back,
                if initial_retraction_amount != 0:
                    prepend_gcode += self.putValue(G = 1, E = initial_retraction_amount, F = initial_retraction_speed * 60) + " ; Extrude filament\n"

                # and retract again, the properly primes the nozzle
                # when changing filament.
                if initial_retraction_amount != 0:
                    prepend_gcode += self.putValue(G = 1, E = -initial_retraction_amount, F = initial_retraction_speed * 60) + " : Retract filament\n"

                # Move the head back
                if current_z < 15:
                    prepend_gcode += self.putValue(G = 1, Z = current_z + 1, F = 300) + "\n"
                prepend_gcode += self.putValue(G = 1, X = x, Y = y, F = 9000) + " ; restore x/y position\n"
                prepend_gcode += self.putValue(G = 1, Z = current_z, F = 300) + " ; move back down to resume height\n"

                if initial_retraction_amount != 0:
                    prepend_gcode += self.putValue(G = 1, E = initial_retraction_amount, F = initial_retraction_speed * 60) + " ; Extrude filament\n"

                if current_extrusion_f != 0:
                    prepend_gcode += self.putValue(G = 1, F = current_extrusion_f) + " ; restore extrusion feedrate\n"
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