from geohash2 import decode_exactly
from shapely.wkt import loads
from pyproj import Proj, transform as pyproj_transform
from math import log10
from json import loads as json_loads
from shapely.geometry import shape


from shapely.geometry import (
    Polygon, 
    Point, 
    MultiPolygon, 
    LineString, 
    MultiLineString, 
    MultiPoint, 
    GeometryCollection
)


BASE32 = '0123456789bcdefghjkmnpqrstuvwxyz'

VALID_WKT_TYPES = [
    'GEOMETRY', 
    'POINT', 
    'MULTIPOINT', 
    'LINESTRING', 
    'MULTILINESTRING', 
    'POLYGON', 
    'MULTIPOLYGON'
]


VALID_SHAPELY_TYPES = (
    Polygon, 
    Point, 
    MultiPolygon, 
    LineString, 
    MultiLineString, 
    MultiPoint, 
    GeometryCollection
)


def validate_geohash(value):
    """Check whether an input value is a valid geohash"""
        
    if len(value) > 12:
        return False
    
    return all(v in BASE32 for v in value)


def detect_geojson(value):
    """Check whether an input value is a valid geohash"""

    if isinstance(value, str):
        if '"features"' in value:
            return True
    return False


def import_geojson(geojson, precision=6):

    output = list()

    for feature in json_loads(geojson)['features']:
        shape_object = shape(feature["geometry"])

        if isinstance(shape_object, Point):
            shape_object = shape_object .buffer(0.1 ** precision).envelope

        output.append(shape_object)

    return output


def validate_wellknowntext(value):
    """Check whether an input value is valid well-known text"""
        
    return any(value.startswith(vt) for vt in VALID_WKT_TYPES)

    
def validate_shapelyobject(value):
    """Check whether an input value is a valid shapely object."""
     
    return issubclass(type(value), VALID_SHAPELY_TYPES)
    
    
def geohash_to_coords(value, precision=6):
    """Convert a geohash to the x and y values of that geohash's bounding box."""
    y, x, y_margin, x_margin = decode_exactly(value)
        
    x_coords = [
        round(x - x_margin, precision),
        round(x - x_margin, precision),
        round(x + x_margin, precision),
        round(x + x_margin, precision)
    ]
        
    y_coords = [
        round(y + y_margin, precision),
        round(y - y_margin, precision),
        round(y - y_margin, precision),
        round(y + y_margin, precision)
    ]

    return [{'exterior': x_coords, 'holes': []}], [{'exterior': y_coords, 'holes': []}]


def shape_to_coords(value, precision=6, wkt=False, is_point=False):
    """
    Convert a shape (a shapely object or well-known text) to x and y coordinates
    suitable for use in Bokeh's `MultiPolygons` glyph.
    
    """
    
    if is_point:
        value = Point(*value).buffer(0.1 ** precision).envelope
    
    x_coords = list()
    y_coords = list()
        
    if wkt:
        value = loads(value)
    if not hasattr(value, '__len__'):
        value = [value] 
        
    for v in value:
        x_dict = dict()
        y_dict = dict()
        if not hasattr(v, 'exterior'):
            v = v.buffer(0)
        x_dict['exterior'] = [round(x, precision) for x in v.exterior.coords.xy[0]]
        x_dict['holes'] = [[round(y, precision) for y in x.coords.xy[0]] for x in v.interiors]
        y_dict['exterior'] = [round(x, precision) for x in v.exterior.coords.xy[1]]
        y_dict['holes'] = [[round(y, precision) for y in x.coords.xy[1]] for x in v.interiors]
        x_coords.append(x_dict)
        y_coords.append(y_dict)

    return x_coords, y_coords


def transform_lon(v, precision):
    v = pyproj_transform(Proj(init='epsg:4326'), Proj(init='epsg:3857'), v, 0)[0]
    return round(v, precision)


def transform_lat(v, precision):
    v = pyproj_transform(Proj(init='epsg:4326'), Proj(init='epsg:3857'), 0, v)[1]
    return round(v, precision)


def transform(v, precision=6, longitude=True):
    return transform_lon(v, precision) if longitude else transform_lat(v, precision)


def coord_to_webmercator(c, precision=6, longitude=True):

    p = transform(0.1 ** precision, precision, longitude)
    p = int(round(log10(p))) * -1

    if not hasattr(c, '__len__'):
        return transform(c, p, longitude)

    output = list()
    for row in c:
        if not hasattr(row, '__len__'):
            row = transform(row, p, longitude)
            output.append(row)
        else:
            newrow = list()
            for v in row:
                v_new = dict()
                v_new['exterior'] = [transform(val, p, longitude) for val in v['exterior']]
                v_new['holes'] = [
                    [transform(val, p, longitude) for val in interior] 
                    for interior in v['holes']
                ]
                newrow.append(v_new)

            output.append(newrow)

    return output
