#!/usr/bin/env python3
 
import os
import sys
import math
import json
import requests
import argparse
import utm
from datetime import datetime

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

def get_evalscript(mask_cloudy=False):
    if mask_cloudy:
        evalscript = """
        //VERSION=3
        function setup() {
          return {
            input: ["B02", "B03", "B04", "SCL"],
            output: { bands: 3 },
          }
        }
        function evaluatePixel(sample) {
          if ([8, 9, 10].includes(sample.SCL)) {
            return [1, 1, 1]
          } else {
            return [2.5 * sample.B04, 2.5 * sample.B03, 2.5 * sample.B02]
          }
        }
        """
    else:
        evalscript = """
        //VERSION=3
        function setup() {
          return {
            input: ["B02", "B03", "B04"],
            output: { bands: 3 },
          }
        }
        function evaluatePixel(sample) {
            return [2.5 * sample.B04, 2.5 * sample.B03, 2.5 * sample.B02]
        }
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

def latlon_to_utm_zone(lon, lat):
    easting, northing, zone_number, zone_letter = utm.from_latlon(lat, lon)
    epsg = 32600 + zone_number if lat >= 0 else 32700 + zone_number
    return easting, northing, epsg

def authenticate():
    client_id, client_secret = get_client_credentials()
    resp = requests.post(TOKEN_URL, data={
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret
    })
    resp.raise_for_status()
    return resp.json()["access_token"]


def request_sentinel_image(lat, lon, level, date_from, date_to, mask=False, width=1024, height=1024):
    # 1. compute tile bounds
    bbox, col, row = get_svt_tile_bbox(lat, lon, level)

    # 2. Convert both corners to UTM
    e0, n0, zone, letter = utm.from_latlon(bbox[1], bbox[0])
    e1, n1, _, _ = utm.from_latlon(bbox[3], bbox[2])
    epsg = 32600 + zone if bbox[1] >= 0 else 32700 + zone
    crs_uri = f"http://www.opengis.net/def/crs/EPSG/0/{epsg}"

    print(f"Box: {bbox}, col: {col}, row: {row}")
    token = authenticate()
    
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "input": {
            "bounds": {
                "properties": {"crs": crs_uri},
                "bbox": [e0, n1, e1, n0],
            },
            "data": [{
                "type": "sentinel-2-l2a",
                "dataFilter": {
                    "timeRange": {
                        "from": date_from,
                        "to": date_to
                    }
                }
            }]
        },
        "output": {
            "width": width,
            "height": height,
            "responses": [
            {
                "identifier": "default",
                "format": {"type": "image/png"},
            }
        ],
        },
        "evalscript": get_evalscript(mask)
    }

    response = requests.post(API_URL, headers=headers, json=payload)
    response.raise_for_status()
    return response.content, col, row

def parse_args():
    parser = argparse.ArgumentParser(description="Fetch Sentinel tile for SVT-aligned bounding box")
    parser.add_argument("-lat", "--lat", type=float, required=True, help="Latitude of the center point")
    parser.add_argument("-lon", "--lon", type=float, required=True, help="Longitude of the center point")
    parser.add_argument("-l", "--level", type=int, required=True, help="SVT tile level")
    parser.add_argument("-f", "--from", dest="date_from", type=str, default="2023-01-01T00:00:00Z", help="Start date (ISO8601)")
    parser.add_argument("-t", "--to", dest="date_to", type=str, default="2024-12-31T00:00:00Z", help="End date (ISO8601)")
    parser.add_argument("-m", "--mask", action=argparse.BooleanOptionalAction, help="Mask cloudy pixels and print them in pure white")
    parser.add_argument("--width", type=int, default=1024, help="Output width in pixels")
    parser.add_argument("--height", type=int, default=1024, help="Output height in pixels")
    return parser.parse_args()

# --- Example usage ---
if __name__ == "__main__":
    args = parse_args()

    try:
        image_bytes, col, row = request_sentinel_image(
            args.lat,
            args.lon,
            args.level,
            args.date_from,
            args.date_to,
            mask=args.mask,
            width=args.width,
            height=args.height
        )
        # Build output directory
        out_dir = os.path.join("out", f"level{args.level:02d}")
        os.makedirs(out_dir, exist_ok=True)
        # Write file
        filename = f"tx_{col}_{row}.jpg"
        filepath = os.path.join(out_dir, filename)
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        print(f"Image saved to {filepath}")
    except requests.HTTPError as e:
        print("Request failed:", e.response.text)
    
