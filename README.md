# Virtual Texture Tools

This project contains a couple of scripts to help prepare Sparse Virtual Texture (SVT) datasets for [Gaia Sky](https://codeberg.org/gaiasky/gaiasky). The format is quite universal, so they can be used equally for other software packages that support virtual texturing.

This project provides two scripts: `split-tiles.py` and `generate-lod.py`.

## Split tiles 

The `split-tiles.py` script takes in a tile size and an image file and splits it up in tiles of the given size. The script can only split images into square (1:1) tiles.

For example, if you have a 1024x512 texture in an image file `image.jpg` that you want to split in 64x64 tiles, you would run:

```bash
split-tiles.py 64 ./image.jpg
```

That will create a list of `tx_[col]_[row].jpg` image files which correspond to the [col,row] tile. In this case, it will produce 128 tile files ($16*8$).

Here are all the options:

```bash
usage: split-tiles [-h] [-c STARTCOL] [-r STARTROW] [-f {jpg,png}] N FILE

Split the given input image into tiles of NxN pixels, named tx_C_R.ext, where C is the column and R is the
row, all zero-based.

positional arguments:
  N                     Resolution of the produced tiles.
  FILE                  The input image. Must have a 1:1 or 2:1 aspect ratio.

options:
  -h, --help            show this help message and exit
  -c STARTCOL, --startcol STARTCOL
                        Starting column to use in the file names of the produced tiles.
  -r STARTROW, --startrow STARTROW
                        Starting row to use in the file names of the produced tiles.
  -f {jpg,png}, --format {jpg,png}
                        Defines the format of the output images. Defaults to jpg.
```

## Generate LOD levels

The `generate-lod.py` script generates the upper LOD level tiles from a directory with the tiles for a certain level. For example, if we move the 128 tiles, which are level-3 tiles ($log_2(8)=3$), to a `level3` directory, we can generate levels 2, 1 and 0 with:

```bash
generate-lod.py 3 ./level3
```

This creates the directories `./level2`, `./level1` and `./level0`, with the corresponding tiles inside.

Here is the full documentation:

```bash
usage: generate-lod [-h] [-f {jpg,png}] level directory

Generate the upper LOD levels from a certain level tile files. Each level L is put in the 'levelL' directory.

positional arguments:
  level                 The level of the input directory.
  directory             The input directory, containing the tiles for the specified level.

options:
  -h, --help            show this help message and exit
  -f {jpg,png}, --format {jpg,png}
                        Defines the format of the output images. Defaults to jpg.
```

## Dependencies

You need Python to run the scripts. The project only depends on `argparse`, `numpy` and `opencv-python`. You can install the right versions with `pip install -r requirements.txt`.

