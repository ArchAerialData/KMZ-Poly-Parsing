# KMZ Polygon Parser

This repository contains a script for extracting polygon areas from a KML/KMZ file.

## Requirements

- Python 3.12+
- `shapely`
- `pyproj`

Install dependencies with:

```bash
pip install shapely pyproj
```

## Usage

Drag and drop a `.kmz` or `.kml` file onto the script or run it from the command line:

```bash
python parse_polygons_to_csv.py your_file.kmz
```

The script creates `polygon_areas.csv` in the same directory, listing each polygon name and its acreage. Column C contains the total acreage in cell `C2`.
