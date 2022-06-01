"""
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

Mike Germain 2022
"""

import re
import sys

# change this value for different layer thicknesses
LAYER_HEIGHT = 0.2

linesChanged = 0

# add delta to the Z-height number in the string and return it
def addZheightGcode(lineString, deltaZ):
    global linesChanged
    zEnd = re.findall('Z[0-9]{1,3}\.[0-9]\\n\Z', lineString)
    zEnd += re.findall('Z[0-9]{1,3}\\n\Z', lineString) # also need to check for non-decimal number
    if len(zEnd) < 1:
        assert False
    zHeight = float(zEnd[0][1:-1]) # strip off the 'Z' and the '\n'
    newZHeightStr = str(round(zHeight + deltaZ, 1))
    if len(newZHeightStr) < 3:
        assert False
    # now put it back into gcode line
    subZstr = zEnd[0]
    newSubZstr = "Z" + newZHeightStr + "\n"
    outString = lineString.replace(subZstr, newSubZstr)
    linesChanged += 1
    return outString

# swap absolute value out for relative value
def swapAbsExtForRel(lineString, absAmtStr, relAmt):
    relAmtStr = "Erel" + str(round(relAmt, 5))
    newLineStr = lineString.replace(absAmtStr, relAmtStr)
    return newLineStr

# swap relative value out for absolute value
def swapRelExtForAbs(lineString, relAmtStr, absAmt):
    global linesChanged
    absAmtStr = "E" + str(round(absAmt, 5))
    newLineStr = lineString.replace(relAmtStr, absAmtStr)
    linesChanged += 1
    return newLineStr


def main(filename, layerToRepeat, numReps):
    global linesChanged
    zHeightToRepeat = round(LAYER_HEIGHT * layerToRepeat, 1)
    deltaZmm = round(LAYER_HEIGHT * numReps, 1)

    print(f"Layer {layerToRepeat} to be repeated {numReps} times. adding total {deltaZmm} mm to model height.")
    lineCount=0
    layerCount=0

    with open(filename, "r") as inputFile:
        fileLines = inputFile.readlines()

    # first go through file and convert all E values to relative instead of cummulative/absolute
    #  find the last extruder reset
    # lineNum = 0
    # firstExtLine = 0
    # lastExtruderResetLine = 0
    # for line in fileLines:
    #     finalExtruderReset = re.findall('G92', line)
    #     if len(finalExtruderReset) > 0:
    #         # found an extruder reset
    #         lastExtruderResetLine = lineNum
    #         print(f"found extruder reset at line {lineNum+1}")
    #     lineNum += 1
    # print(f"Last extruder reset line:{lastExtruderResetLine}")

    # now start after last reset and convert all extrusion amounts to relative
    absExtAmount = 0.0
    numRelChanges = 0
    lineNum = 0
    totalExtrusionBefore = 0
    for line in fileLines[lineNum:]:
        extruderReset = re.findall('G92', line)
        if len(extruderReset) > 0:
            absExtAmount = 0.0 # the extruder has been reset, we must also reset our absolute amount
            # print(f"reset extruder amt at line {lineNum+1}")
        else:
            extrusionAmtFound = re.findall('E[0-9]{1,6}\.[0-9]{0,6}', line)
            if len(extrusionAmtFound) > 0:
                # found a line with extrusion command
                extAmtFloat = float(extrusionAmtFound[0][1:])
                relExtAmtFloat = round(extAmtFloat - absExtAmount, 5)
                totalExtrusionBefore += relExtAmtFloat # keep track of total file extrusion for before/after comparison
                newLineString = swapAbsExtForRel(line, extrusionAmtFound[0], relExtAmtFloat)
                fileLines[lineNum] = newLineString
                # set the new abs amount for next iteration
                absExtAmount = extAmtFloat
                numRelChanges += 1
        lineNum += 1

    print(f"Changed to relative: {numRelChanges} lines")

    # find all Z height changes and shift later layers by deltaZmm
    lineNum = 0
    layerLineNum = 0
    nextLayerLineNum = 0
    for line in fileLines:
        lineCount += 1
        foundZComand = re.findall('Z[0-9]{1,3}\.[0-9]\\n\Z', line)
        foundZComand += re.findall('Z[0-9]{1,3}\\n\Z', line) # also need to check for non-decimal number
        if len(foundZComand) == 1: # findall returns a list, empty if it finds nothing
            layerCount += 1
            zHeight = float(foundZComand[0][1:-1]) # strip off the 'Z' and the '\n'
            if zHeight == zHeightToRepeat:
                print(f"Found layer {layerToRepeat} at height {zHeight} mm at GCODE line {lineNum}")
                layerLineNum = lineNum-1 # minus 1 to catch the pre comment too
            elif zHeight > zHeightToRepeat:
                if nextLayerLineNum == 0:
                    nextLayerLineNum = lineNum-1 # minus 1 to catch the pre comment too
                # add deltaZmm to rest of layer Z heights
                newGcodeLine = addZheightGcode(line, deltaZmm)
                fileLines[lineNum] = newGcodeLine
        elif len(foundZComand) > 1:
            print(foundZComand)
            assert False
        lineNum += 1

    # chunk to repeat
    # Note: first line has the original Z height, which must be incremented
    repeatedLayerLines = fileLines[layerLineNum:nextLayerLineNum]

    # collect first part of file, with initial layer to be repeated
    outputFileLines = fileLines[:nextLayerLineNum]
    # print(f"added lines {0} to {nextLayerLineNum}")

    # now add the repeated part x # of times
    for rep in range(0, numReps):
        delta = round((rep + 1) * LAYER_HEIGHT, 1)
        if len(str(delta)) < 3:
            assert False
        # modify first line with delta Z
        # First line is acomment, so modify second[1] line
        firstLine = repeatedLayerLines[1]
        newFirstLine = addZheightGcode(firstLine, delta)
        outputFileLines.append(repeatedLayerLines[0]) # add comment line
        outputFileLines.append(newFirstLine) # add modded command line
        outputFileLines += repeatedLayerLines[2:] # add rest of layer chunk
        print(f"copied layer {layerToRepeat} code up to line {len(outputFileLines)}")

    # now add the rest of the layers, each already offset by deltaZmm
    outputFileLines += fileLines[nextLayerLineNum:]
    print(f"added final {len(fileLines[nextLayerLineNum:])} lines")

    # now convert extrusion amounts back to absolute
    # Note: extrusion command 'E' has been replaced with "Erel"
    # so it is easy to find all the ones we touched before
    lineNum = 0
    cummulativeExt = 0
    totalExtrusionAfter = 0
    for line in outputFileLines[lineNum:]:
        extruderReset = re.findall('G92', line)
        if len(extruderReset) > 0:
            cummulativeExt = 0.0 # the extruder has been reset, we must also reset our cummulative amount
            # print(f"reset cummulitive extruder amt at line {lineNum+1}")
        # find the Erel commands we made earlier. Need to include optional '-' for negative (retractions)
        else:
            extrusionAmtFound = re.findall('Erel-?[0-9]{1,3}\.[0-9]{0,6}', line)
            if len(extrusionAmtFound) > 0:
                relAmtFloat = float(extrusionAmtFound[0][4:])
                totalExtrusionAfter += relAmtFloat # keep track of total file extrusion for before/after comparison
                cummulativeExt += relAmtFloat
                newLineString = swapRelExtForAbs(line, extrusionAmtFound[0], cummulativeExt)
                outputFileLines[lineNum] = newLineString
        lineNum += 1

    print(f"\nTotal lines modified: {linesChanged}")
    print(f"Total filament before: {round(totalExtrusionBefore, 1)} mm")
    print(f"Total filament after : {round(totalExtrusionAfter, 1)} mm")
    print(f"Total added filament : {round(totalExtrusionAfter-totalExtrusionBefore, 1)} mm")

    # write to file output
    outFilename = "layerRepeaterOutput.gcode"
    with open(outFilename, "w") as outputFile:
        for line in outputFileLines:
            outputFile.write(line)

    print(f"Saved to file: {outFilename}\n")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("\nUsage: python layerRepeater.py <filename> <layer number> <number of repetitions>\n")
    else:
        filename = sys.argv[1]
        layerToRepeat = int(sys.argv[2])
        numReps = int(sys.argv[3])
        print("\n--- layerRepeater.py ---")
        print(f"input file: {filename}")
        main(filename, layerToRepeat, numReps)
