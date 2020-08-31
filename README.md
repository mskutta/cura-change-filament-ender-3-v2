# Overview

I needed a way to easily change filament mid print on the Creality Ender 3 v2.
The initial release of the Ender 3 v2 firmware did not support the M600 filament change and M0 was very buggy.

I use Cura and wanted to create a Post Processing Modify G-Code extension to handle filament change for me and to get around the initial bugs for the Ender 3 v2 firmware. This extension has since morphed something similar to what M600 supports, but with more features.

Here were the requirements I had for filament change:

* A single pause that requires a single press of the control knob on the Ender 3v2 to continue. This lowers the total inteaction time with the printer. (as of now text prompts are not supported on the Ender 3v2 display. A single pause eliminates the number of steps and confusion as to what step you are on.)
* Ability to remove the filament without waiting to re-heat the nozzle.
* Ability to load the filament without waiting to re-heat the nozzle.
* Ability to leave the printer in a pause state waiting for filament change
* The purge proces should not reqire interaction.
* Avoid moving the Z axis to prevent backlash issues.

The above requirements were solved by:

1. Initially retract to prevent blobs.  This retraction is configurable.
1. Do a later retraction to remove the filament.  The retraction is set by default to 30mm to move the filament just far enough away from the nozzle to support later manual removal.  THe retraction can be set to completely remove the filament out of the extruder.  I did not set that as the default to prevent the ejected filament from getting tangled.
1. Allow the nozzle to cool down
1. Park the nozzle outside of the print area.  This gives space to work under the nozzle and a space for purged filament to go.  This also eliminates the need to move the Z axis if changing filament on short prints. THe nozzle is parked at X245. This is configurable.  As this coordinate is outside the print area for the Ender 3 v2, software endstops are disabled.
1. The user then manually removes the filament and then loads new filament, inserting it as far as possible. This is done without heating the nozzle.
1. The button on the Ender 3v2 display is then pressed a single time to continue.
1. The nozzle heats back up. Waiting until the target temperature of the nozzle is reached.
1. The filament is then purged a default of 50mm.  This can be configured.  I found this distance was enough to purge out the old filament. The filament is purged to the side of the build surface.
1. The nozzle is then quickly primed, weakening the hold between the nozzle onto the purged filament.
1. The nozzle then moves back to the next print positon, software endstops are enabled. The purged filament should then drop to the side of the print area.

# Installation

To use the "Change Filament Ender 3 v2" Post Processing Modify G-Code extension, the **ChangeFilamentEnder3v2.py** needs to be copied to Cura. To find the location to put this file, open Cura and naviate to "Help / Show Configuration Folder" in the menu.  The Cura configuration folder should open. From there, navigate to the **scripts** subfolder.  Paste the **ChangeFilamentEnder3v2.py** file there.  Re-open Cura so it will recognize the extension.

# Usage

TODO

# Notes

I also wanted a way to load filament at the beginning of the print with very little user interaction.  I also wanted the ability to easily remove the filament at the end of a print without re-heating the nozzle.  I added g-code handling this to the start and end scripts for the Ender 3 v2 printer in Cura.  I included those .gcode scripts here also:

* Ender3v2Start.gcode
* Ender3v2End.gcode



