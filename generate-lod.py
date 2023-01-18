#! /usr/bin/env python

# This script takes in a location with a bunch of tiles
# previously split (with split-tiles.py) and generates
# all the levels to the top.

import argparse
import os
import numpy as np
import cv2
import sys
import re

# Instantiate the parser
parser = argparse.ArgumentParser(description='Generate the upper LOD levels from a certain level tile files. Each level L is put in the \'levelL\' directory.')

# Required positional arguments
parser.add_argument('level', type=int,
                    help='The level of the input directory.')
parser.add_argument('directory', type=str,
                    help='The input directory, containing the tiles for the specified level.')

args = parser.parse_args()


"""
Processes the tiles of the given level, and produces the tiles of level-1.
"""
def process_level(level, dir):
    if not os.path.exists(dir):
        print("Directory for level %d not found: %s" % (level, dir))
        sys.exit(-1)

    print("Processing level: %d (%s)" % (level, dir))

    directory = os.fsencode(dir)

    maxcol = 0
    maxrow = 0
    for file in os.listdir(directory):
        filename = os.fsdecode(file)
        ok = re.search("^tx_\d+_\d+\.\w+", filename)
        if ok is not None:
            name = os.path.splitext(filename)[0]
            tokens = name.split('_')
            col = int(tokens[1])
            row = int(tokens[2])
            if col > maxcol:
                maxcol = col
            if row > maxrow:
                maxrow = row

    # MxN matrix 
    M = maxrow + 1
    N = maxcol + 1
    # Create matrix of tiles
    tiles = [[ 0 for i in range(N) ] for j in range(M)]
    # Fill it with files
    for file in os.listdir(directory):
        filename = os.fsdecode(file)
        ok = re.search("^tx_\d+_\d+\.\w+", filename)
        if ok is not None:
            name = os.path.splitext(filename)[0]
            tokens = name.split('_')
            col = int(tokens[1])
            row = int(tokens[2])
            tiles[row][col] = filename

    l = level - 1
    leveldir = "level" + str(l)
    if not os.path.exists(leveldir):
        os.makedirs(leveldir)

    # Every 4 tiles, we join them into one, and downsize it.
    for i in range(0, N, 2): # col
        for j in range(0, M, 2): # row
            file00 = os.path.join(dir, tiles[j][i])
            im00 = cv2.imread(file00)   
            file10 = os.path.join(dir, tiles[j][i+1])
            im10 = cv2.imread(file10)   
            file01 = os.path.join(dir, tiles[j+1][i])
            im01 = cv2.imread(file01)   
            file11 = os.path.join(dir, tiles[j+1][i+1])
            im11 = cv2.imread(file11)

            # Actually stitch
            # im00-im10 -> im0
            # im01-im11 -> im1
            im0= np.concatenate((im00, im10), axis=1)
            im1 = np.concatenate((im01, im11), axis=1)
            im = np.concatenate((im0, im1), axis=0)

            tilesize = im00.shape[0]
            # Resize to tile size
            tile = cv2.resize(im, dsize=(tilesize, tilesize), interpolation=cv2.INTER_CUBIC) 
    
            outfilename = "tx_" + str(int(i/2)) + "_" + str(int(j/2)) + ".jpg"
            out = os.path.join(leveldir, outfilename)
            cv2.imwrite(out, tile)

    if l > 0:
        # Process next level up.
        process_level(l, leveldir)

# Start with requested level
process_level(args.level, args.directory)