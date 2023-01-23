#! /usr/bin/env python

# Convert SVT column, row, and level to longitude and latitude, and vice-versa.

import argparse
import math
import sys


# Instantiate the parser
parser = argparse.ArgumentParser(description='Convert SVT column, row, and level to longitude and latitude, and vice-versa.')

parser.add_argument('-c', '--column', type=int,
                    help='Column in level.')
parser.add_argument('-r', '--row', type=int,
                    help='Row in level.')
parser.add_argument('-lon', type=int,
                    help='The longitude in [-180, 180].')
parser.add_argument('-lat', type=int,
                    help='The latitude in [-90, 90].')
parser.add_argument('-l', '--level', type=int, required=True,
                    help='The SVT level.')

args = parser.parse_args()

# Level must be there
l = args.level

# Number of columns and rows
nc = pow(2.0, l + 1)
nr = pow(2.0, l)

def uvToLatLon(u, v):
    lon = u * 360.0 - 180.0
    lat = v * 180.0 - 90.0
    return lon, lat

def latLonToUV(lat, lon):
    u = (lon + 180.0) / 360.0
    v = (lat + 90.0) / 180.0
    return u, v

def colRowToUV(c, r, nc, nr):
    u = c / nc
    v = 1.0 - (r / nr)
    return u, v

def extent(a, b):
    return [abs(b[0] - a[0]), abs(b[1] - a[1])]


if args.lon is not None and args.lat is not None:
    lon = args.lon
    lat = args.lat
    # UV
    u, v = latLonToUV(lat, lon)

elif args.column is not None and args.row is not None:
    c = args.column
    r = args.row
    # UV
    u, v = colRowToUV(c, r, nc, nr)

else:
    print("Nothing to convert!")
    parser.print_help()
    sys.exit(-1)


# Convert UV to [lon,lat]
lon = u * 360.0 - 180.0
lat = v * 180.0 - 90.0

# Convert UV to [col,row] 
c = u * nc
r = (1.0 - v) * nr

# Second mapping for lat,lon
c2 = c + 1
r2 = r + 1
u2, v2 = colRowToUV(c2, r2, nc, nr)
lon2, lat2 = uvToLatLon(u2, v2)


uv1 = [u, v]
uv2 = [u2, v2]
coord1 = [lon, lat]
coord2 = [lon2, lat2]
colrow1 = [int(c), int(r)]
colrow2 = [int(c2), int(r2)]

print("Level:                   %d" % l)
print("col/row:                 %s -> %s (extent %s)" % (colrow1, colrow2, extent(colrow1, colrow2)))
print("Lon/lat (start -> end):  %s -> %s (extent %s)" % (coord1, coord2, extent(coord1, coord2)))
print("UV (start -> end):       %s -> %s (extent %s)" % (uv1, uv2, extent(uv1, uv2)))
