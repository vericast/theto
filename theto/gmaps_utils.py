from math import sin, pi, log, floor


def lat_rad(lat):
    """Convert a latitude to radians (for estimating zoom factor for Google Maps)."""
    sine = sin(lat * pi / 180.)
    rad_x2 = log((1 + sine) / (1 - sine)) / 2.
    return max(min(rad_x2, pi), -pi) / 2.

    
def zoom(map_px, world_px, fraction):
    """Calculate the zoom factor for Google Maps."""
    try:
        return floor(log(map_px / world_px / fraction) / log(2))
    except ZeroDivisionError:
        return None

    
def estimate_zoom(plot_width, x_bounds, y_bounds, height_max=600, zoom_max=21, world_dim=256):
    """
    Given a desired plot width and data source(s), estimate the best zoom factor for Google Maps.
    
    Parameters:
     
    plot_width (int): desired plot width, in pixels
    x_bounds (tuple): min and max of x axis
    y_bounds (tuple): min and max of y axis
    height_max (int): maximum height allowable for the plot
    zoom_max (int): maximum zoom factor (21 is the maximum Google Maps allows)
    world_dim (int): the number of dimensions fo the world map (256 is the Google default)
        
    Returns:
        
    Zoom factor (int): the zoom factor to be used in the call to Google Maps
    y_center (float): the central latitude for the plot
    x_center (float): the central longitude for the plot
    plot_height (int): the height to be used for the plot
        
    """

    xmin, xmax = x_bounds
    ymin, ymax = y_bounds
    y_range = abs(ymax - ymin)
    x_range = abs(xmax - xmin)
    if (x_range == 0) or (y_range == 0):
        plot_height = height_max
    else:
        plot_height = int((plot_width / x_range) * y_range)
    if plot_height < plot_width:
        plot_height = plot_width
    if plot_height > height_max:
        plot_height = height_max
    y_center = (ymin + ymax) / 2.0
    x_center = (xmin + xmax) / 2.0

    lat_fraction = (lat_rad(ymax) - lat_rad(ymin)) / pi
    lng_diff = xmax - xmin
    lng_fraction = ((lng_diff + 360) if (lng_diff < 0) else lng_diff) / 360.

    lat_zoom = zoom(plot_height, world_dim, lat_fraction)
    lng_zoom = zoom(plot_width, world_dim, lng_fraction)

    if (lat_zoom is None) and (lng_zoom is None):
        return zoom_max, y_center, x_center, plot_height
    elif lat_zoom is None:
        return int(min(lng_zoom, zoom_max)), y_center, x_center, plot_height
    elif lng_zoom is None:
        return int(min(lat_zoom, zoom_max)), y_center, x_center, plot_height
    else:
        return int(min(lat_zoom, lng_zoom, zoom_max)), y_center, x_center, plot_height
