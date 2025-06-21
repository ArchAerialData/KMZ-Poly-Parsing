import os
import sys
import zipfile
import xml.etree.ElementTree as ET
import logging
import re
import csv

try:
    from shapely.geometry import Polygon
    from shapely.ops import transform
except ImportError:  # pragma: no cover - dependency check
    print("The 'shapely' package is required. Install it with 'pip install shapely'.")
    raise

try:
    from pyproj import Transformer
except ImportError:  # pragma: no cover - dependency check
    print("The 'pyproj' package is required. Install it with 'pip install pyproj'.")
    raise

# Setup logging
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "LOG.txt")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

# Transformer for coordinate projection (lat/lon to meters)
_transformer = Transformer.from_crs("epsg:4326", "epsg:3857", always_xy=True)

# KML namespace
KML_NS = {"kml": "http://www.opengis.net/kml/2.2"}

def _extract_kml_from_kmz(kmz_path: str) -> bytes:
    """Extract KML data from a KMZ file."""
    with zipfile.ZipFile(kmz_path) as z:
        for name in z.namelist():
            if name.lower().endswith(".kml"):
                with z.open(name) as f:
                    return f.read()
    raise RuntimeError("No KML file found inside KMZ")

def parse_coordinates(coord_text: str) -> list:
    """Parse KML coordinates text into a list of (lon, lat) tuples."""
    coords = []
    for part in coord_text.strip().split():
        pieces = part.split(',')
        if len(pieces) >= 2:
            lon, lat = map(float, pieces[:2])
            coords.append((lon, lat))
    return coords

def extract_polygon_coords(polygon_el) -> tuple:
    """Extract exterior and interior coordinates from a Polygon element."""
    outer_ring = polygon_el.find('kml:outerBoundaryIs/kml:LinearRing/kml:coordinates', KML_NS)
    if outer_ring is None:
        return None, []
    exterior = parse_coordinates(outer_ring.text)
    
    inner_rings = polygon_el.findall('kml:innerBoundaryIs/kml:LinearRing/kml:coordinates', KML_NS)
    interiors = [parse_coordinates(inner.text) for inner in inner_rings if inner.text]
    
    return exterior, interiors

def parse_area_from_description(description: str) -> tuple:
    """Parse area value and unit from description (e.g., 'Area: 5.2 sq mi')."""
    match = re.search(r"Area:\s*([\d\.]+)\s*([a-zA-Z\s]+)", description, re.IGNORECASE)
    if match:
        value = float(match.group(1))
        unit = match.group(2).lower()
        return value, unit
    return None

def convert_to_acres(value: float, unit: str) -> float:
    """Convert area value to acres based on unit."""
    unit = unit.lower()
    if unit == 'acres':
        return value
    elif unit in ['sq mi', 'square miles']:
        return value * 640
    elif unit == 'hectares':
        return value * 2.47105
    elif unit in ['sq km', 'square kilometers']:
        return value * 247.105
    elif unit in ['sq ft', 'square feet', 'sqft']:
        return value / 43560
    elif unit in ['sq m', 'square meters', 'square metres', 'sq meter', 'sq metre']:
        return value / 4046.86
    else:
        raise ValueError(f"Unknown unit: {unit}")

def main():
    # Check for drag-and-drop input
    if len(sys.argv) != 2:
        print("Usage: drag and drop a KMZ or KML file onto this script")
        sys.exit(1)
    
    input_path = sys.argv[1]
    if not os.path.isfile(input_path):
        print(f"Provided path is not a file: {input_path}")
        sys.exit(1)
    
    # Handle KMZ or KML input
    if input_path.lower().endswith('.kmz'):
        try:
            kml_data = _extract_kml_from_kmz(input_path)
        except Exception as e:
            logging.error(f"Failed to extract KML from KMZ: {e}")
            print("Error extracting KML from KMZ. See log for details.")
            sys.exit(1)
    elif input_path.lower().endswith('.kml'):
        with open(input_path, 'rb') as f:
            kml_data = f.read()
    else:
        print("Please provide a KMZ or KML file.")
        sys.exit(1)
    
    # Parse KML data
    try:
        root = ET.fromstring(kml_data)
    except ET.ParseError as e:
        logging.error(f"Failed to parse KML: {e}")
        print("Error parsing KML. See log for details.")
        sys.exit(1)
    
    results = []
    for pm in root.findall('.//kml:Placemark', KML_NS):
        polygon = pm.find('.//kml:Polygon', KML_NS)
        if polygon is None:
            continue
        
        # Extract name
        name_el = pm.find('kml:name', KML_NS)
        name = name_el.text.strip() if name_el is not None else 'Unnamed'
        
        # Extract description for possible area
        desc_el = pm.find('kml:description', KML_NS)
        description = desc_el.text if desc_el is not None else ''
        
        # Try to parse area from description
        area_info = parse_area_from_description(description)
        
        # Get polygon coordinates
        exterior, interiors = extract_polygon_coords(polygon)
        if not exterior:
            logging.warning(f"Polygon '{name}' has no coordinates.")
            continue
        
        # Determine area in acres
        if area_info:
            value, unit = area_info
            try:
                area_acres = convert_to_acres(value, unit)
            except ValueError:
                logging.warning(f"Unknown unit '{unit}' for polygon '{name}', calculating area instead.")
                poly = Polygon(exterior, interiors)
                poly_m = transform(_transformer.transform, poly)
                area_m2 = poly_m.area
                area_acres = area_m2 / 4046.86  # Convert sq meters to acres
        else:
            # Calculate area if not provided
            poly = Polygon(exterior, interiors)
            poly_m = transform(_transformer.transform, poly)
            area_m2 = poly_m.area
            area_acres = area_m2 / 4046.86
        
        results.append((name, area_acres))
    
    if not results:
        print("No polygons found in the KML file.")
        sys.exit(0)
    
    # Write results to CSV with total column
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, 'polygon_areas.csv')

    total_acres = sum(area for _, area in results)

    with open(csv_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Polygon Name', 'Total Acreage', 'Total'])
        first = True
        for name, area in results:
            row = [name, f"{area:.2f}", '']
            if first:
                row[2] = f"{total_acres:.2f}"
                first = False
            writer.writerow(row)
    
    print(f"CSV report generated: {csv_path}")

if __name__ == "__main__":
    main()