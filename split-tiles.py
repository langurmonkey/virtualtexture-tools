#! /usr/bin/env python

# This script splits up the given input image into
# NxM tiles, and names them "tx_i_j.ext". 

import argparse
import os.path
import numpy as np
import cv2
import sys

def is_valid_file(parser, arg):
    if not os.path.exists(arg):
        parser.error("The file %s does not exist!" % arg)
    else:
        return arg  # return the string

def load_image( infilename ) :
    return cv2.imread(infilename)


# Instantiate the parser
parser = argparse.ArgumentParser(description='Split the given input image into tiles of NxN pixels, named tx_C_R.ext, where C is the column and R is the row, all zero-based.')

# Required positional arguments
parser.add_argument('N', type=int,
                    help='Resolution of the produced tiles.')
parser.add_argument('file', metavar="FILE",
                    type=lambda x: is_valid_file(parser, x),
                    help='The input image. Must have a 1:1 or 2:1 aspect ratio.')

args = parser.parse_args()

print("Input: %s" % args.file)
im = load_image(args.file)

print("Mode: ", im.shape)


# Split image
M = args.N
N = args.N

# Check divisibility
if im.shape[0] % N != 0:
    print("Error: image height not divisible by tile size: %d -> %d" % (im.shape[0], N))
    sys.exit(1)
if im.shape[1] % M != 0:
    print("Error: image width not divisible by tile size: %d -> %d" % (im.shape[1], M))
    sys.exit(1)

tiles = [im[x:x+M,y:y+N] for x in range(0,im.shape[0],M) for y in range(0,im.shape[1],N)]

cols = im.shape[1] / M
rows = im.shape[0] / N

c = 0
r = 0
for count, tile in enumerate(tiles):
    fname = 'tx_' + str(c) + '_' + str(r) + '.jpg'
    print("Writing %s" % fname)
    cv2.imwrite(fname, tile)

    c = int((c + 1) % cols)
    if c == 0:
        r = r + 1
