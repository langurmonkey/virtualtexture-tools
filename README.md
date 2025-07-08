# Virtual Texture Tools

This project contains a couple of scripts to help prepare Sparse Virtual Texture (SVT) datasets for [Gaia Sky](https://codeberg.org/gaiasky/gaiasky). The format is quite universal, so they can be used equally for other software packages that support virtual texturing.

This project provides three scripts:

- `split-tiles.py` -- Given a large image, split it into tiles down to a certain level.
- `generate-lod.py` -- Given the tiles for a given level, create the LOD levels above.
- `sentinel-query.py` -- Download true color images from the Sentinel-2 satellite and save them with the correct format. 
- `tile-info.py` -- Convert coordinates to SVT tiles, and vice-versa.

## Split tiles 

The `split-tiles.py` script takes in a tile size and an image file and splits it up in tiles of the given size. The script can only split images into square (1:1) tiles.

For example, if you have a 1024x512 texture in an image file `image.jpg` that you want to split in 64x64 tiles, you would run:

```bash
split-tiles.py 64 ./image.jpg
```

That will create a list of `tx_[col]_[row].jpg` image files which correspond to the [col,row] tile. In this case, it will produce 128 tile files ($16*8$). 

You can specify the output format with `-f` and the quality (if the format is JPG) with `-q`. Here are all the options:

```bash
usage: split-tiles [-h] [-c STARTCOL] [-r STARTROW] [-f {jpg,png}] [-q QUALITY] RESOLUTION FILE

Split the given input image into tiles of NxN pixels, named tx_C_R.ext, where C is the column and R is the
row, all zero-based.

positional arguments:
  RESOLUTION            Resolution of the produced tiles.
  FILE                  The input image. Must have a 1:1 or 2:1 aspect ratio.

options:
  -h, --help            show this help message and exit
  -c STARTCOL, --startcol STARTCOL
                        Starting column to use in the file names of the produced tiles.
  -r STARTROW, --startrow STARTROW
                        Starting row to use in the file names of the produced tiles.
  -f {jpg,png}, --format {jpg,png}
                        Defines the format of the output images. Defaults to jpg.
  -q QUALITY, --quality QUALITY
                        If the format is JPG, this defines the quality setting in [1,100]. Defaults to 95.
```

## Generate LOD levels

The `generate-lod.py` script generates the upper LOD level tiles from a directory with the tiles for a certain level. For example, if we move the 128 tiles, which are level-3 tiles ($log_2(sqrt(64))=3$, we use two root images, and each root has 64 images at level 3; [0:1, 1:4, 2:16, 3:64]), to a `level3` directory, we can generate levels 2, 1 and 0 with:

```bash
generate-lod.py 3 ./level3
```

This creates the directories `./level2`, `./level1` and `./level0`, with the corresponding tiles inside.

You can specify the output format with `-f` and the quality (if the format is JPG) with `-q`. Here are all the options:

```bash
usage: generate-lod [-h] [-f {jpg,png}] [-q QUALITY] LEVEL DIRECTORY

Generate the upper LOD levels from a certain level tile files. Each level L is put in the 'levelL' directory.

positional arguments:
  LEVEL                 The level of the input directory.
  DIRECTORY             The input directory, containing the tiles for the specified level.

options:
  -h, --help            show this help message and exit
  -f {jpg,png}, --format {jpg,png}
                        Defines the format of the output images. Defaults to jpg.
  -q QUALITY, --quality QUALITY
                        If the format is JPG, this defines the quality setting in [1,100]. Defaults to 95.
```

## Sentinel downloader

The `sentinel-query.py` script connects to the [CDSE Sentinel Hub Processing API](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Process.html) to download [True Color]( https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Process/Examples/S2L2A.html#true-color) satellite images.

The script has two modes:

- **Single mode**---Download a single tile given a pair of (latitude, longitude) coordinates and an SVT level.
- **Multi mode**---Download all tiles between two levels L0 and L1 where L0 < L1. In this mode, you give it the two levels and a pair of (latitude, longitude) coordinates and the script will get all tiles recursively from L0 to L1. In this mode, it is possible to skip tiles that have no land (water tiles) by using the flag `--skip_water`.

The script includes an option to mask out cloudy pixels (`--mask_clouds`). If you get a cloudy image, try playing around with the from and to dates (`-f` and `-t`). For instance, you can get cloudless images of Heidelberg, Germany, during the summer months.

You need to [create an account](https://documentation.dataspace.copernicus.eu/Registration.html) in the CDSE website and then create an OAuth token, which will give you a client ID and a client secret ([more info here](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Overview/Authentication.html#python)). Then, set up the following environment variables:

```bash
export CLIENT_ID="my-client-id"
export CLIENT_SECRET="my-client-secret"
```

Then, you are ready to run the script. Here are the options:

```bash
usage: sentinel-query.py [-h] -lat LAT -lon LON [-l0 LEVEL0] [-l1 LEVEL1] [-l LEVEL] [-f DATE_FROM]
                         [-t DATE_TO] [-m | --mask_clouds | --no-mask_clouds]
                         [-s | --skip_water | --no-skip_water] [--width WIDTH] [--height HEIGHT]

Fetch Sentinel tile for SVT-aligned bounding box. The program has two modes. In single mode, provide a
single level in -l to get a single tile with the given coordinates. In multi mode, provide two levels
-l0 and -l1 to download all tiles between those levels (both included).

options:
  -h, --help            show this help message and exit
  -lat, --lat LAT       Latitude of the center point.
  -lon, --lon LON       Longitude of the center point.
  -l0, --level0 LEVEL0  The upper level in multi mode. Downloads all tiles between levels -l0 and -l1,
                        both levels included. -l1 is required for this to work, and -l1 > -l0.
  -l1, --level1 LEVEL1  The lower level in multi mode. Downloads all tiles between levels -l0 and -l1,
                        both levels included. -l0 is required for this to work, and -l0 < -l1.
  -l, --level LEVEL     SVT tile level. If this is present, single mode is activated.
  -f, --from DATE_FROM  Start date. Format can be ISO8601 (e.g. 2023-01-01T00:00:00Z) or YYYYMMDD (e.g.
                        20230101).
  -t, --to DATE_TO      End date. Format can be ISO8601 (e.g. 2023-01-01T00:00:00Z) or YYYYMMDD (e.g.
                        20230101).
  -m, --mask_clouds, --no-mask_clouds
                        Mask cloudy pixels and print them in pure red color.
  -s, --skip_water, --no-skip_water
                        Skip tiles that are only water. Only works in multi mode (-l0, -l1).
  --width WIDTH         Output width in pixels.
  --height HEIGHT       Output height in pixels.
```

For example, if you want to get the tile for latitude=41.33 and longitude=1.89 at level 9, you would run:

```bash
➜ ./sentinel-query.py --lat 41.33 --lon 1.89 --level 9
Box: [1.7578125, 41.1328125, 2.109375, 41.484375], col: 517, row: 138
Image saved to out/level09/tx_517_138.jpg
```

As you can see, images are saved to `out/level{level}/tx_{col}_{row}.jpg`

## Tile information

The `tile-info.py` script can convert from (latitude, longitude, level) to tile coordinates (column, row), and vice-versa. It also outputs UV coordinates, and a WKT and GeoJSON polygon.

```bash
usage: tile-info.py [-h] [-c COLUMN] [-r ROW] [-lon LON] [-lat LAT] -l LEVEL

Convert SVT column, row, and level to longitude and latitude, and vice-versa.

options:
  -h, --help           show this help message and exit
  -c, --column COLUMN  Column index of the tile.
  -r, --row ROW        Row index of the tile.
  -lon LON             Longitude in [-180, 180].
  -lat LAT             Latitude in [-90, 90].
  -l, --level LEVEL    SVT level.
```


## Dependencies

You need Python to run the scripts. The project depends on `argparse`, `numpy`, and `opencv-python`. In order to use the `sentinel-query.py` script, you also need `Pillow`, `sentinelhub`, and `global_land_mask`. You can install the right versions with `pip install -r requirements.txt`.

