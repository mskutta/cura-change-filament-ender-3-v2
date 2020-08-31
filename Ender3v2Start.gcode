; Ender 3 v2 Custom Start G-code
M104 S{material_print_temperature_layer_0} ; Set Extruder temperature
M190 S{material_bed_temperature_layer_0} ; Wait for Heat Bed temperature
G92 E0 ; Reset Extruder
G28 ; Home all axes

; Purge
M109 S{material_print_temperature_layer_0} ; Wait for Extruder temperature
M211 S0 ; disable endstops
G1 F9000 X245 Y10 ; move head away
G91 ; Relative positioning
G1 F300 E50 ; purge filament
G4 S10 ; releave pressure
G1 F1500 E5 ; Extrude filament (prime)
G1 F1500 E-5 ; Retract filament (prime)
G90 ; Absolute positionning
M400 ; finish moves
M211 S1 ; enable endstops
G92 E0 ; Reset Extruder

G29 ; Auto Bed Leveling
M109 S{material_print_temperature_layer_0} ; Wait for Extruder temperature
; M900 K1.0 ; Linear Advance K value

G1 Z2.0 F3000 ; Move Z Axis up little to prevent scratching of Heat Bed
G1 X0.1 Y20 Z0.3 F5000.0 ; Move to start position
G1 F1500 E5 ; Extrude filament (prime)
G1 X0.1 Y200.0 Z0.3 F1500.0 E15 ; Draw the first line
G1 X0.4 Y200.0 Z0.3 F5000.0 ; Move to side a little
G1 X0.4 Y20 Z0.3 F1500.0 E30 ; Draw the second line
G92 E0 ; Reset Extruder
G1 Z2.0 F3000 ; Move Z Axis up little to prevent scratching of Heat Bed
G1 X5 Y20 Z0.3 F5000.0 ; Move over to prevent blob squish