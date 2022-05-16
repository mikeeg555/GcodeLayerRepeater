# GcodeLayerRepeater
layerRepeater.py

This script loads a GCODE file and copies a given layer some number of times.

The process is as follows:

    - Load the GCODE lines.
    
    - Convert all model extrusion and retraction values from cummulative/absolute
        to relative. This makes the layer insertion much simpler.
        
    - Add the total delta-Z (layer height x number repetitions) to all layers
        past the repeated layer.
        
    - Insert the repeated layer x number of times.
    
    - Go back though the new file lines and convert all the relative extrusion
        values back to cummulative/absolute.
        
    - Save output gcode file.
    
Usage: python layerRepeater.py \<filename> \<layer number> \<number of repetitions>

Mike Germain 2022
