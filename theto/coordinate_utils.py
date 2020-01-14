from shapely.wkt import loads, dumps
from pyproj import Proj, transform as pyproj_transform
from math import log10
from json import loads as json_loads
from shapely.geometry import shape, box
from functools import partial
from shapely.ops import transform as shapely_transform

from shapely.geometry import (
    Polygon, 
    Point, 
    MultiPolygon, 
    LineString,
    LinearRing,
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
    'LINEARRING'
    'MULTILINESTRING', 
    'POLYGON', 
    'MULTIPOLYGON'
]


VALID_SHAPELY_TYPES = (
    Polygon, 
    Point, 
    MultiPolygon, 
    LineString,
    LinearRing,
    MultiLineString, 
    MultiPoint, 
    GeometryCollection
)

webmercator_project = partial(
    pyproj_transform,
    Proj(init='epsg:4326'),  # source coordinate system
    Proj(init='epsg:3857')  # destination coordinate system
)


def to_webmercator(pol):
    return shapely_transform(webmercator_project, pol)


def divide_range_decode(coordinate_range, b):
    mid = (coordinate_range[0] + coordinate_range[1]) / 2
    if b:
        coordinate_range[0] = mid
    else:
        coordinate_range[1] = mid


def geohash_to_centroid(geohash, return_error=True):
    binary_string = ''.join([format(BASE32.index(v), 'b').zfill(5) for v in geohash])
    latitude_range = [-90.0, 90.0]
    longitude_range = [-180.0, 180.0]
    is_even_bit = True

    for j, v in enumerate(binary_string):
        if is_even_bit:
            divide_range_decode(longitude_range, v != '0')
        else:
            divide_range_decode(latitude_range, v != '0')
        is_even_bit = not is_even_bit

    latitude = (latitude_range[0] + latitude_range[1]) / 2
    longitude = (longitude_range[0] + longitude_range[1]) / 2

    if return_error:
        latitude_error = abs(latitude_range[0] - latitude_range[1]) / 2
        longitude_error = abs(longitude_range[0] - longitude_range[1]) / 2
        return latitude, longitude, latitude_error, longitude_error
    else:
        return latitude, longitude


def validate_geohash(value):
    """Check whether an input value is a valid geohash"""
        
    if len(value) > 12:
        return False
    
    return all(v in BASE32 for v in value)


def detect_geojson(value):
    """Check whether an input value is a valid geohash"""

    if isinstance(value, str):
        try:
            _ = json_loads(value)
            return True
        except Exception:
            return False
    return False


def import_geojson(feature, precision=6):

    json_dict = json_loads(feature)
    if 'geometry' in json_dict:
        shape_object = shape(json_dict["geometry"])
    elif 'coordinates' in json_dict:
        shape_object = shape(json_dict)
    else:
        raise KeyError('Unable to infer key for coordinate values.')

    if isinstance(shape_object, Point):
        shape_object = shape_object.buffer(0.1 ** precision).envelope

    return shape_object


def validate_wellknowntext(value):
    """Check whether an input value is valid well-known text"""
        
    return any(value.startswith(vt) for vt in VALID_WKT_TYPES)

    
def validate_shapelyobject(value):
    """Check whether an input value is a valid shapely object."""
     
    return issubclass(type(value), VALID_SHAPELY_TYPES)
    

def geohash_to_shape(value):
    """Convert a geohash to a shapely object."""

    y, x, y_margin, x_margin = geohash_to_centroid(value)

    minx = x - x_margin
    maxx = x + x_margin
    miny = y - y_margin
    maxy = y + y_margin

    return box(minx, miny, maxx, maxy)


def geohash_to_coords(value, precision=6):
    """Convert a geohash to the x and y values of that geohash's bounding box."""
    y, x, y_margin, x_margin = geohash_to_centroid(value)
        
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


def validate_latlon_pair(value):
    """
    Check to make sure value is a tuple or list of length 2,
    where the first element is a longitude and the second.
    is a latitude.
    """

    if len(value) != 2:
        raise ValueError('List inputs are assumed to be coordinate pairs. This list has more than two elements.')

    if not (-180.0 <= value[0] <= 180.0):
        raise ValueError(
            ' '.join([
                'The first element of the list is assumed to be longitude (x-coordinates),',
                'but this element is outside acceptable bounds (-180.0, 180.0)'
            ])
        )

    if not (-90.0 <= value[0] <= 90.0):
        raise ValueError(
            ' '.join([
                'The second element of the list is assumed to be latitude (y-coordinates),',
                'but this element is outside acceptable bounds (-90.0, 90.0)'
            ])
        )

    return True


def process_input_value(value):
    """
    Router function for values: take an arbitrary value,
    determine what kind of input it is, and return
    a standardized coordinate output.

    """

    if type(value) == str:
        if validate_geohash(value):
            return geohash_to_shape(value)
        elif validate_wellknowntext(value):
            return loads(value)
        else:
            raise ValueError('String inputs must be either a geohash or well-known text.')
    elif type(value) in (tuple, list):
        if validate_latlon_pair(value):
            return Point(*value)
    elif validate_shapelyobject(value):
        return value
    else:
        raise ValueError('Unrecognizeable input: {}.'.format(str(value)))


def polygon_to_nested_list(pol):

    ext_x, ext_y = zip(*list(pol.exterior.coords))
    x, y = [list(ext_x)], [list(ext_y)]
    for interior in pol.interiors:
        int_x, int_y = zip(*interior.coords)
        x.append(list(int_x))
        y.append(list(int_y))
    return x, y


def shape_to_nested_list(shp, buffer=0.000001):
    if shp.geometryType() in ('LineString', 'LinearRing'):
        xs, ys = polygon_to_nested_list(shp.buffer(buffer))
        xs, ys = [xs], [ys]
    elif shp.geometryType() == 'Point':
        xs, ys = polygon_to_nested_list(shp.buffer(buffer).envelope)
        xs, ys = [xs], [ys]
    elif shp.geometryType() == 'Polygon':
        xs, ys = polygon_to_nested_list(shp)
        xs, ys = [xs], [ys]
    elif shp.geometryType().startswith('Multi') or (shp.geometryType() == 'GeometryCollection'):
        xs, ys = list(zip(*[shape_to_nested_list(pol) for pol in shp]))
        xs, ys = [x[0] for x in xs], [y[0] for y in ys]
    else:
        raise NotImplementedError('Unrecognized shapely shape type.')
    return xs, ys


def dumps_if_shapely(ob):
    if validate_shapelyobject(ob):
        return dumps(ob)
    return ob
