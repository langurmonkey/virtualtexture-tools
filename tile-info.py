#!/usr/bin/env python3

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

def tileExtent(col, row, nc, nr):
    u0, v0 = colRowToUV(col, row, nc, nr)         # top-left
    u1, v1 = colRowToUV(col + 1, row + 1, nc, nr) # bottom-right
    lon0, lat0 = uvToLatLon(u0, v0)
    lon1, lat1 = uvToLatLon(u1, v1)
    return (lon0, lat0, lon1, lat1), (u0, v0, u1, v1)

def extent(a, b):
    return [abs(b[0] - a[0]), abs(b[1] - a[1])]

# Argument parsing
parser = argparse.ArgumentParser(description='Convert SVT column, row, and level to longitude and latitude, and vice-versa.')
parser.add_argument('-c', '--column', type=int, help='Column index of the tile.')
parser.add_argument('-r', '--row', type=int, help='Row index of the tile.')
parser.add_argument('-lon', type=float, help='Longitude in [-180, 180].')
parser.add_argument('-lat', type=float, help='Latitude in [-90, 90].')
parser.add_argument('-l', '--level', type=int, required=True, help='SVT level.')

args = parser.parse_args()
l = args.level

# Number of columns and rows at this level
nc = 2 ** (l + 1)
nr = 2 ** l

# Case 1: Input is lat/lon
if args.lon is not None and args.lat is not None:
    lat = args.lat
    lon = args.lon

    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        print("Latitude must be in [-90, 90], longitude in [-180, 180]")
        sys.exit(1)

    u, v = latLonToUV(lat, lon)
    c = u * nc
    r = (1.0 - v) * nr

    col = int(math.floor(c))
    row = int(math.floor(r))

    (lon0, lat0, lon1, lat1), (u0, v0, u1, v1) = tileExtent(col, row, nc, nr)

    print(f"Level:                   {l}")
    print()
    print(f"Input point:             lat={lat}, lon={lon}")
    print(f"Tile indices:            col={col}, row={row}")
    print(f"Tile extent (lon/lat):   ({lon0}, {lat0}) -> ({lon1}, {lat1})")
    print()
    print("WKT POLYGON:")
    print(f"  POLYGON(({lon0} {lat0}, {lon1} {lat0}, {lon1} {lat1}, {lon0} {lat1}, {lon0} {lat0}))")
    print()
    print("UV extent:")
    print(f"  UV start:              ({u0}, {v0})")
    print(f"  UV end:                ({u1}, {v1})")
    print(f"  UV size:               {extent((u0, v0), (u1, v1))}")

# Case 2: Input is col/row
elif args.column is not None and args.row is not None:
    col = args.column
    row = args.row

    if not (0 <= col < nc) or not (0 <= row < nr):
        print(f"Invalid tile indices at level {l}: col must be in [0,{nc-1}], row in [0,{nr-1}]")
        sys.exit(1)

    (lon0, lat0, lon1, lat1), (u0, v0, u1, v1) = tileExtent(col, row, nc, nr)

    print(f"Level:                   {l}")
    print()
    print(f"Tile indices:            col={col}, row={row}")
    print(f"Tile extent (lon/lat):   ({lon0}, {lat0}) -> ({lon1}, {lat1})")
    print()
    print("WKT POLYGON:")
    print(f"  POLYGON(({lon0} {lat0}, {lon1} {lat0}, {lon1} {lat1}, {lon0} {lat1}, {lon0} {lat0}))")
    print()
    print("UV extent:")
    print(f"  UV start:              ({u0}, {v0})")
    print(f"  UV end:                ({u1}, {v1})")
    print(f"  UV size:               {extent((u0, v0), (u1, v1))}")

# Invalid input
else:
    print("You must provide either:")
    print("  -lat, -lon, -l     (to get the tile containing that point), or")
    print("  -c, -r, -l         (to get the geographic extent of a tile).")
    parser.print_help()
    sys.exit(1)
