#!/usr/bin/env python3
 
import os
import sys
import math
import json
import argparse
import geopy
import numpy as np
from geopy.geocoders import Nominatim
from PIL import Image
from datetime import datetime
from global_land_mask import globe
from sentinelhub import (
    SHConfig,
    DataCollection,
    SentinelHubCatalog,
    SentinelHubRequest,
    SentinelHubStatistical,
    BBox,
    bbox_to_dimensions,
    CRS,
    MimeType,
    Geometry,
)

output_dir = "out"

def get_lat_lon(location_name):
    geolocator = Nominatim(user_agent="geoapi")
    location = geolocator.geocode(location_name)
    if location:
        return (location.latitude, location.longitude)
    else:
        return None

def tile_has_land(lat0, lon0, lat1, lon1, resolution=10):
    """
    Returns True if ANY point within the lat/lon rectangle is land.
    """
    import numpy as np
    lats = np.linspace(lat0, lat1, resolution)
    lons = np.linspace(lon0, lon1, resolution)
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    return globe.is_land(lat_grid, lon_grid).any()

def get_client_credentials():
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")

    if not client_id or not client_secret:
        print("Error: Environment variables CLIENT_ID and CLIENT_SECRET must be set.", file=sys.stderr)
        sys.exit(1)

    return client_id, client_secret

# --- CONFIG ---
TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
API_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"

def get_evalscript():
    evalscript = """
    //VERSION=3
    function setup() {
      return {
        input: ["B02", "B03", "B04", "dataMask"],
        output: { bands: 4 },
      }
    }
    // Contrast enhance / highlight compress

    const maxR = 3.0; // max reflectance
    const midR = 0.13;
    const sat = 1.2;
    const gamma = 1.8;
    const scalefac = 10000;

    function evaluatePixel(smp) {
      const rgbLin = satEnh(sAdj(smp.B04/scalefac), sAdj(smp.B03/scalefac), sAdj(smp.B02/scalefac));
      return [sRGB(rgbLin[0]), sRGB(rgbLin[1]), sRGB(rgbLin[2]), smp.dataMask];
    }

    function sAdj(a) {
      return adjGamma(adj(a, midR, 1, maxR));
    }

    const gOff = 0.01;
    const gOffPow = Math.pow(gOff, gamma);
    const gOffRange = Math.pow(1 + gOff, gamma) - gOffPow;

    function adjGamma(b) {
      return (Math.pow((b + gOff), gamma) - gOffPow)/gOffRange;
    }

    // Saturation enhancement
    function satEnh(r, g, b) {
      const avgS = (r + g + b) / 3.0 * (1 - sat);
      return [clip(avgS + r * sat), clip(avgS + g * sat), clip(avgS + b * sat)];
    }

    function clip(s) {
      return s < 0 ? 0 : s > 1 ? 1 : s;
    }

    //contrast enhancement with highlight compression
    function adj(a, tx, ty, maxC) {
      var ar = clip(a / maxC, 0, 1);
      return ar * (ar * (tx/maxC + ty -1) - ty) / (ar * (2 * tx/maxC - 1) - tx/maxC);
    }

    const sRGB = (c) => c <= 0.0031308 ? (12.92 * c) : (1.055 * Math.pow(c, 0.41666666666) - 0.055);
    """
        
    return evalscript

def get_svt_tile_bbox(lat, lon, level):
    nc = 2 ** (level + 1)
    nr = 2 ** level

    u = (lon + 180.0) / 360.0
    v = (lat + 90.0) / 180.0

    col = int(u * nc)
    row = int((1.0 - v) * nr)

    u0 = col / nc
    v0 = 1.0 - (row / nr)
    u1 = (col + 1) / nc
    v1 = 1.0 - ((row + 1) / nr)

    lon0 = u0 * 360.0 - 180.0
    lat0 = v0 * 180.0 - 90.0
    lon1 = u1 * 360.0 - 180.0
    lat1 = v1 * 180.0 - 90.0

    return [lon0, lat1, lon1, lat0], col, row

def tile_exists(lat, lon, level):
    global output_dir

    _, col, row = get_svt_tile_bbox(lat, lon, level)

    level_dir = os.path.join(output_dir, f"level{level:02d}")
    filename = f"tx_{col}_{row}.jpg"
    filepath = os.path.join(level_dir, filename)
    return os.path.isfile(filepath), filename, filepath


def request_sentinel_true_col(lat, lon, level, date_from, date_to, width=1024, height=1024):
    client_id, client_secret = get_client_credentials()
    config = SHConfig()
    config.sh_client_id = client_id
    config.sh_client_secret = client_secret
    config.sh_token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    config.sh_base_url = "https://sh.dataspace.copernicus.eu"

    bbox, col, row = get_svt_tile_bbox(lat, lon, level)

    aoi_bbox = BBox(bbox=bbox, crs=CRS.WGS84)
    aoi_size = (width, height)

    S2l3_cloudless_mosaic = DataCollection.define_byoc(
        collection_id="5460de54-082e-473a-b6ea-d5cbe3c17cca"
    )
    request_true_color = SentinelHubRequest(
        evalscript=get_evalscript(),
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=S2l3_cloudless_mosaic,
                time_interval=(date_from, date_to),
            )
        ],
        responses=[SentinelHubRequest.output_response("default", MimeType.PNG)],
        bbox=aoi_bbox,
        size=aoi_size,
        config=config,
        data_folder="./cache",
    )

    true_col_imgs = request_true_color.get_data(save_data=False)

    return true_col_imgs[0], col, row

def download_tile(level, lat, lon, args):
    exists, fname, fpath = tile_exists(lat, lon, level)
    if exists and not args.overwrite:
        print(f"Skipping tile, file exists: {fpath}.")
        return
        
    image_bytes, col, row = request_sentinel_true_col(
        lat,
        lon,
        level,
        args.date_from,
        args.date_to,
        width=args.width,
        height=args.height
    )
    arr_rgb = image_bytes[:, :, :3]  # Drop alpha channel
    # Convert to Image and save as JPEG
    img = Image.fromarray(arr_rgb)

    # Build output directory
    global output_dir
    level_dir = os.path.join(output_dir, f"level{level:02d}")
    os.makedirs(level_dir, exist_ok=True)
    # Write file
    filename = fname
    filepath = fpath
    img.save(filepath, quality=88)

    if not exists:
        print(f"Image saved to {filepath}")
    else:
        print(f"Image saved to {filepath} (ow)")

def parse_date(date_str):
    # Try ISO 8601 first
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y%m%d"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(
        f"Invalid date format: {date_str}. Use ISO8601 (e.g. 2023-01-01T00:00:00Z) or YYYYMMDD (e.g. 20230101)."
    )

    
""" Current tile number """
current_tile = 0
""" Number of skipped tiles """
skipped_tiles = 0
""" Total tiles to fetch """
total_tiles = 0

def process_tile_rec(latitude, longitude, level, l1, keep_water=False):
    global current_tile
    global skipped_tiles
    global total_tiles
    
    current_tile += 1
    bbox, col, row = get_svt_tile_bbox(latitude, longitude, level)
    
    # Compute center longitude and latitude
    minlat = min(bbox[1], bbox[3])
    maxlat = max(bbox[1], bbox[3])
    minlon = min(bbox[0], bbox[2])
    maxlon = max(bbox[0], bbox[2])
    span_lat = (maxlat - minlat) / 2.0
    span_lon = (maxlon - minlon) / 2.0
    center_lat = minlat + span_lat
    center_lon = minlon + span_lon

    has_land = tile_has_land(minlat, minlon, maxlat, maxlon)
    if not has_land and not keep_water:
        print(f"Skipping water tile L{level} ({col},{row})")
        skipped_tiles += 1

    print(f"Request {level}, {center_lat}, {center_lon} ({current_tile * 100.0 / total_tiles:.2f}%)")

    if has_land or keep_water:
        download_tile(level, center_lat, center_lon, args)

    # Children
    lats = span_lat / 2.0
    lons = span_lon / 2.0
    if level < l1:
        # Subdivide into 4
        process_tile_rec(center_lat - lats, center_lon - lons, level + 1, l1, keep_water)
        process_tile_rec(center_lat - lats, center_lon + lons, level + 1, l1, keep_water)
        process_tile_rec(center_lat + lats, center_lon - lons, level + 1, l1, keep_water)
        process_tile_rec(center_lat + lats, center_lon + lons, level + 1, l1, keep_water)
    

def level_mode(args):
    level = args.level
    cols = (2 ** level) * 2
    rows = 2 ** level
    global current_tile, total_tiles, skipped_tiles
    total_tiles = cols * rows

    print(f"Num tiles: {total_tiles} ({cols} columns, {rows} rows)")

    current_tile = 0
    lat0 = 90.0
    lon0 = -180.0
    step = 180.0 / rows
    for col in range(cols):
        for row in range(rows):
            lon = lon0 + col * step
            lat = lat0 - row * step

            bbox, col, row = get_svt_tile_bbox(lat, lon, level)
            # Compute center longitude and latitude
            minlat = min(bbox[1], bbox[3])
            maxlat = max(bbox[1], bbox[3])
            minlon = min(bbox[0], bbox[2])
            maxlon = max(bbox[0], bbox[2])
            span_lat = (maxlat - minlat) / 2.0
            span_lon = (maxlon - minlon) / 2.0
            center_lat = minlat + span_lat
            center_lon = minlon + span_lon

            lat = center_lat
            lon = center_lon

            print(f"Tile: tx_{col}_{row}  ({lat}, {lon}) - {current_tile + 1}/{total_tiles}, {(current_tile + 1) * 100.0 / total_tiles:.2f}%")

            has_land = tile_has_land(minlat, minlon, maxlat, maxlon)
            if not has_land and not args.keep_water:
                print(f"Skipping water tile L{level} ({col},{row})")
                skipped_tiles += 1

            if has_land or args.keep_water:
                download_tile(level, lat, lon, args)
                current_tile += 1
        

def parse_args():
    parser = argparse.ArgumentParser(description="Fetch Sentinel tile for SVT-aligned bounding box. The program has two modes. In single mode, provide a single level in -l to get a single tile with the given coordinates. In multi mode, provide two levels -l0 and -l1 to download all tiles between those levels (both included).")
    parser.add_argument("-lat", "--latitude", type=float, help="Latitude of the center point. Required if --location is not provided.")
    parser.add_argument("-lon", "--longitude", type=float, help="Longitude of the center point. Required if --location is not provided.")
    parser.add_argument("--location", type=str, help="Location name. The latitude and longitude of this location will be resolved using Nominatim (OpenStreetMap). Required if -lat/-lon are not provided.")
    parser.add_argument("-l0", "--level0", type=int, required=False, help="The upper level in multi mode. Downloads all tiles between levels -l0 and -l1, both levels included. -l1 is required for this to work, and -l1 > -l0.")
    parser.add_argument("-l1", "--level1", type=int, required=False, help="The lower level in multi mode. Downloads all tiles between levels -l0 and -l1, both levels included. -l0 is required for this to work, and -l0 < -l1.")
    parser.add_argument("-l", "--level", type=int, required=False, help="SVT tile level. If this is present, single mode is activated.")
    parser.add_argument("-f", "--from", dest="date_from", type=parse_date, default=datetime(2024, 1, 1), help="Start date. Format can be ISO8601 (e.g. 2023-01-01T00:00:00Z) or YYYYMMDD (e.g. 20230101).")
    parser.add_argument("-t", "--to", dest="date_to", type=parse_date, default=datetime(2025, 6, 1), help="End date. Format can be ISO8601 (e.g. 2023-01-01T00:00:00Z) or YYYYMMDD (e.g. 20230101).")
    parser.add_argument("-o", "--overwrite", default=False, action="store_true", help="Overwrite images if they already exist.")
    parser.add_argument("-k", "--keep-water", default=False, action="store_true", help="Keep tiles that are only water. By default, all-water tiles are discarded. Only works in multi mode (-l0, -l1) and in level mode (no location provided).")
    parser.add_argument("--width", type=int, default=1024, help="Output width in pixels.")
    parser.add_argument("--height", type=int, default=1024, help="Output height in pixels.")
    args = parser.parse_args()

    # Mode
    single_mode = args.level is not None
    multi_mode = args.level0 is not None and args.level1 is not None

    if not (single_mode ^ multi_mode):
        parser.error("You must provide either both -l0 and -l1, or -l (but not both).")

    # Location
    loc = args.location is not None
    coords = args.latitude is not None and args.longitude is not None

    level_mode = False
    if not (loc ^ coords):
        if multi_mode:
            parser.error("Level mode needs a single level (--level).")

        print("No location provided. We are about to enter 'level mode', where a level is downloaded for the whole Earth.")
        print(f"Are you **SURE** you want to get **ALL** level {args.level} tiles for the whole Planet?")
        response = input("(Y/n): ")
        level_mode = response == "" or response == "y" or response == "Y"
        if not level_mode:
            parser.error("You must provide either both --latitude and --longitude, or --location (but not both).")

    if coords:
        lat = args.latitude
        lon = args.longitude
    else:
        # Resolve.
        ll = get_lat_lon(args.location)
        if ll is None:
            parser.error(f"Could not resolve latitude and longitude for location '{args.location}'")
        else :
            print(f"Resolved '{args.location}' to {ll}.")

        lat = ll[0]
        lon = ll[1]
    

    return args, single_mode, level_mode, lat, lon

if __name__ == "__main__":
    args, mode_single, mode_level, lat, lon = parse_args()

    if mode_level:
        print("Level mode activated")
        print(f" - Downloading all tiles of level {args.level}")
        # Get all tiles at this level.
        level_mode(args)
        print(f"Done. Downloaded {current_tile} tiles, skipped {skipped_tiles} water tiles.")

    elif mode_single:
        print("Single mode activated")
        print(f"   level:{args.level}  lon:{lon}  lat:{lat}")
        # Single mode, just download one tile.
        download_tile(args.level, lat, lon, args)

    else:
        # Multi mode, download tiles between two levels.
        if args.level0 >= args.level1:
            print(f"-l0 ({args.level0}) must be less than -l1 ({args.level1}).")

        print("Multi mode activated")
        print(f"   levels:{args.level0}-{args.level1}  lon:{lon}  lat:{lat}")

        ops = 0
        for l in range(args.level0, args.level1 + 1):
            ops = ops + 4 ** (l - args.level0)

        print(f"We need to fetch {ops} tiles")

        total_tiles = ops
        process_tile_rec(lat, lon, args.level0, args.level1, keep_water=args.keep_water)

        print(f"Done. Downloaded {current_tile} tiles, skipped {skipped_tiles} water tiles.")
