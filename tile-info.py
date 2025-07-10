#!/usr/bin/env python3

"""
SVT tile coordinate converter for spherical virtual textures.

This utility converts between:
- (col, row, level) tile coordinates and their corresponding geographic coordinates (longitude, latitude).
- (longitude, latitude, level) coordinates and their corresponding tile indices. This can also be given as a location name (cities, landmarks, etc.) to be resolved via Nominatim.

Supports full-sphere virtual textures with longitude in [-180°, 180°] and latitude in [-90°, 90°].
"""

import argparse
import math
import sys
import json
from geopy.geocoders import Nominatim

def get_lat_lon(location_name):
    geolocator = Nominatim(user_agent="geoapi")
    location = geolocator.geocode(location_name)
    if location:
        return (location.latitude, location.longitude)
    else:
        return None

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
    u0, v0 = colRowToUV(col, row, nc, nr)
    u1, v1 = colRowToUV(col + 1, row + 1, nc, nr)
    lon0, lat0 = uvToLatLon(u0, v0)
    lon1, lat1 = uvToLatLon(u1, v1)
    return (lon0, lat0, lon1, lat1), (u0, v0, u1, v1)

def extent(a, b):
    return [abs(b[0] - a[0]), abs(b[1] - a[1])]

def parse_args():
    # Argument parsing
    parser = argparse.ArgumentParser(description='Convert SVT column, row, and level to longitude and latitude, and vice-versa.')
    parser.add_argument('-c', '--column', type=int, help='Column index of the tile.')
    parser.add_argument('-r', '--row', type=int, help='Row index of the tile.')
    parser.add_argument("-lat", "--latitude", type=float, help="Latitude of the center point. Required if --location is not provided.")
    parser.add_argument("-lon", "--longitude", type=float, help="Longitude of the center point. Required if --location is not provided.")
    parser.add_argument("--location", type=str, help="Location name. The latitude and longitude of this location will be resolved using Nominatim (OpenStreetMap). Required if -lat/-lon are not provided.")
    parser.add_argument('-l', '--level', type=int, required=True, help='SVT level.')

    args = parser.parse_args()

    # Location
    loc = args.location is not None
    coords = args.latitude is not None and args.longitude is not None

    if loc and coords:
        parser.error("You can provide either both --latitude and --longitude, or --location (but not both).")

    lat = None
    lon = None
    if coords:
        lat = args.latitude
        lon = args.longitude
    elif loc:
        # Resolve.
        ll = get_lat_lon(args.location)
        if ll is None:
            parser.error(f"Could not resolve latitude and longitude for location '{args.location}'")
        else :
            print(f"Resolved '{args.location}' to {ll}.")

        lat = ll[0]
        lon = ll[1]

    return args, lat, lon

if __name__ == "__main__":
    args, latitude, longitude = parse_args()

    l = args.level
    nc = 2 ** (l + 1)
    nr = 2 ** l

    # Determine tile from lat/lon or directly
    if longitude is not None and latitude is not None:
        lat = latitude
        lon = longitude

        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            print("Latitude must be in [-90, 90], longitude in [-180, 180]")
            sys.exit(1)

        u, v = latLonToUV(lat, lon)
        c = u * nc
        r = (1.0 - v) * nr

        col = int(math.floor(c))
        row = int(math.floor(r))

    elif args.column is not None and args.row is not None:
        col = args.column
        row = args.row

        if not (0 <= col < nc) or not (0 <= row < nr):
            print(f"Invalid tile indices at level {l}: col must be in [0,{nc-1}], row in [0,{nr-1}]")
            sys.exit(1)

    else:
        print("You must provide either:")
        print("  -lat, -lon, -l     (to get the tile containing that point), or")
        print("  --location, -l     (to get the tile containing that location), or")
        print("  -c, -r, -l         (to get the geographic extent of a tile).")
        sys.exit(1)

    # Now that we have col/row, compute everything
    (lon0, lat0, lon1, lat1), (u0, v0, u1, v1) = tileExtent(col, row, nc, nr)
    lat_extent = abs(lon0 - lon1)
    lat_extent_m = lat_extent * 110574.0
    lon_extent = abs(lon0 - lon1)
    lon_extent_m = lon_extent * math.cos(math.radians(lat0)) * 111320.0
    tile_size = 1024.0

    print(f"Level:                   {l}")
    print()
    print(f"Tile indices:           col={col}, row={row}")
    print(f"Tile coords (lon/lat):  ({lon0:.3f}, {lat0:.3f}) -> ({lon1:.3f}, {lat1:.3f})")
    print(f"Tile extent [deg]:      ({lon_extent:.3f}, {lat_extent:.3f})")
    print(f"Tile extent [m]:        ({lon_extent_m:.3f}, {lat_extent_m:.3f})")
    print(f"Tile size [px]:         {int(tile_size)}^2")
    print(f"Resolution [m/px]:      ({lon_extent_m/tile_size:.3f}, {lat_extent_m/tile_size:.3f})")
    print()
    print("WKT POLYGON:")
    print(f"  POLYGON(({lon0} {lat0}, {lon1} {lat0}, {lon1} {lat1}, {lon0} {lat1}, {lon0} {lat0}))")
    print()
    print("GeoJSON Polygon:")
    geojson = {
        "type": "Polygon",
        "coordinates": [[ [lon0, lat0], [lon1, lat0], [lon1, lat1], [lon0, lat1], [lon0, lat0] ]]
    }
    print(json.dumps(geojson))
    print()
    print("UV extent:")
    print(f"  UV start:              ({u0}, {v0})")
    print(f"  UV end:                ({u1}, {v1})")
    print(f"  UV size:               {extent((u0, v0), (u1, v1))}")
