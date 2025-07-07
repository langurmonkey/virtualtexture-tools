#! /usr/bin/env python

"""
SVT tile coordinate converter for spherical virtual textures.

This utility converts between:
- (col, row, level) tile coordinates and their corresponding geographic coordinates (longitude, latitude)
- (longitude, latitude, level) coordinates and their corresponding tile indices

Supports full-sphere virtual textures with longitude in [-180°, 180°] and latitude in [-90°, 90°].
"""

import argparse
import math
import sys


# Instantiate the parser
parser = argparse.ArgumentParser(description='Convert SVT column, row, and level to longitude and latitude, and vice-versa.')

parser.add_argument('-c', '--column', type=int,
                    help='Column in level.')
parser.add_argument('-r', '--row', type=int,
                    help='Row in level.')
parser.add_argument('-lon', type=float,
                    help='The longitude in [-180, 180].')
parser.add_argument('-lat', type=float,
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

# Get the integer tile indices of the tile that contains the point
col = int(math.floor(c))
row = int(math.floor(r))

# UV of top-left corner
u0, v0 = colRowToUV(col, row, nc, nr)
# UV of bottom-right corner
u1, v1 = colRowToUV(col + 1, row + 1, nc, nr)
# UV
uv1 = [u0, v0]
uv2 = [u1, v1]

# Convert UVs to lon/lat
lon0, lat0 = uvToLatLon(u0, v0)  # top-left
lon1, lat1 = uvToLatLon(u1, v1)  # bottom-right

# Polygon in WKT format: (lon lat) space-separated, counter-clockwise
print(f"Level:                   {l}")
print()
print(f"Input point:             lat={lat}, lon={lon}")
print(f"Tile indices:            col={col}, row={row}")
print(f"Tile extent (lon/lat):   ({lon0}, {lat0}) -> ({lon1}, {lat1})")
print()
print("WKT POLYGON:")
print(f"  POLYGON(({lon0} {lat0}, {lon1} {lat0}, {lon1} {lat1}, {lon0} {lat1}, {lon0} {lat0}))")
print()
print(f"UV (start -> end):       {uv1} -> {uv2} (extent {extent(uv1, uv2)})")
