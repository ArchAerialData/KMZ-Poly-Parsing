# KMZ Polygon Parser

This repository contains a script for extracting polygon areas from a KML/KMZ file.

## Requirements

- Python 3.12+
- `shapely`
- `pyproj`
- `openpyxl`

Install dependencies with:

```bash
pip install shapely pyproj openpyxl
```

## Usage

Drag and drop a `.kmz` or `.kml` file onto the script or run it from the command line:

```bash
python parse_polygons_to_csv.py your_file.kmz
```

The script creates `polygon_areas.xlsx` in the same directory, listing each polygon name and its acreage. Cell `C2` contains a SUM formula for the acreage column, and cell `D2` displays the total area converted to square feet, square miles, and square meters.
