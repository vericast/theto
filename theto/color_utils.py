from bokeh.colors import named
from numpy import array, repeat, argmax, linspace

NAMED_COLORS = {color: getattr(named, color).to_hex() for color in named.__all__}


def minmax_scale(x, out_range=(-1, 1)):
    if type(x) != array:
        x = array(x)
        
    domain = min(x), max(x)
    y = (x - (domain[1] + domain[0]) / 2) / (domain[1] - domain[0])
    
    return y * (out_range[1] - out_range[0]) + (out_range[1] + out_range[0]) / 2


def hex_to_rgb(hexcode):
    """'#FFFFFF' -> [255,255,255] """
    # Pass 16 to the integer function for change of base
    return [int(hexcode[i:i+2], 16) for i in range(1, 6, 2)]


def rgb_to_hex(rgb):
    """ [255,255,255] -> '#FFFFFF' """
    # Components need to be integers for hex to make sense
    rgb = [int(x) for x in rgb]
    return "#"+"".join(["0{0:x}".format(v) if v < 16 else "{0:x}".format(v) for v in rgb])


def check_color(color):
    if color is None:
        return True
    if color in NAMED_COLORS.keys():
        return True
    else:
        try:
            _ = hex_to_rgb(color)
            return True
        except (ValueError, IndexError, TypeError):
            return False
        

def check_numeric(val):
    if isinstance(val, (int, float)):
        return True
    elif isinstance(val, (list, tuple, set)):
        return all(isinstance(x, (int, float)) for x in val)
    else:
        return False

    
def color_gradient(vals, start_hex, end_hex, mid_hex='#ffffff', trans=None):
    """
    Returns a gradient list of colors between two hex colors (adapted 
    from https://bsou.io/posts/color-gradients-with-python). Gradient 
    is spaced linearly with the numerical values of (optionally transformed) 
    `vals`. If `vals` include both positive negative numbers, gradient goes 
    from `start_hex` to `mid_hex` (default of white at zero), to `end_hex`.
    Values for start_hex and end_hex should be the full six-digit color string, 
    including the number sign ("#FFFFFF").
    
    """
    
    # convert vals to array
    sarr = array(vals).astype('float64')
    has_neg = min(vals) < 0
    has_pos = max(vals) > 0
    
    # colors in RGB form
    s = hex_to_rgb(start_hex)
    f = hex_to_rgb(end_hex)
    m = hex_to_rgb(mid_hex)

    if not all([has_neg, has_pos]):
        if trans is not None:
            sarr = trans(minmax_scale(sarr, out_range=(1e-10, 10)))
        sarr = minmax_scale(sarr, out_range=(0, 1))
        
        return [rgb_to_hex(rgb) for rgb in zip(*[(s[j] + sarr * (f[j] - s[j])) for j in range(3)])]
    else:
        sarr_neg = sarr[sarr <= 0]
        sarr_pos = sarr[sarr >= 0]
        if trans is not None:
            sarr_pos = trans(minmax_scale(sarr_pos, out_range=(1e-10, 10)))
            sarr_neg = trans(minmax_scale(sarr_neg, out_range=(1e-10, 10)))

        sarr_pos = minmax_scale(sarr_pos, out_range=(0, 1))
        sarr_neg = minmax_scale(sarr_neg, out_range=(0, 1))
        
        sarr_new = repeat(mid_hex, sarr.shape[0])
        sarr_new[sarr >= 0] = [
            rgb_to_hex(rgb) 
            for rgb in zip(*[(m[j] + sarr_pos * (f[j] - m[j])) for j in range(3)])
        ]
        sarr_new[sarr <= 0] = [
            rgb_to_hex(rgb) 
            for rgb in zip(*[(s[j] + sarr_neg * (m[j] - s[j])) for j in range(3)])
        ]

        return sarr_new


def order_records(x_coords, y_coords):
    n_records = len(x_coords)
    record_inds = list(range(n_records))
    a = array(list(zip(x_coords, y_coords)))

    inds = array([True] * n_records)
    current_ind = 0
    ind_order = list()

    while any(inds):
        inds[current_ind] = False
        ind_order.append(current_ind)
        dists = ((a[current_ind, :] - a) ** 2).sum(axis=1) ** 0.5
        dists[~inds] = -1
        current_ind = argmax(dists)

    order_dict = dict(zip([record_inds[ind] for ind in ind_order], record_inds))
    score = [order_dict[ind] for ind in record_inds]
    return score


def _v(m1, m2, hue):
    hue = hue % 1.0
    if hue < (1 / 6):
        return m1 + (m2 - m1) * hue * 6.0
    if hue < 0.5:
        return m2
    if hue < (2 / 3):
        return m1 + (m2 - m1) * ((2 / 3) - hue) * 6.0
    return m1


def hls_to_rgb(h, l, s):
    """
    Adapted from https://github.com/python/cpython/blob/master/Lib/colorsys.py
    """
    if s == 0.0:
        return l, l, l
    if l <= 0.5:
        m2 = l * (1.0 + s)
    else:
        m2 = l + s - (l * s)
    m1 = 2.0 * l - m2
    r, g, b = _v(m1, m2, h + (1.0 / 3.0)), _v(m1, m2, h), _v(m1, m2, h - (1.0 / 3.0))
    return int(r * 255.0), int(g * 255.0), int(b * 255.0)


def rgb_to_hex_sep(r, g, b):
    return "#{0:02x}{1:02x}{2:02x}".format(r, g, b)


def hls_palette(n_colors=6, h=.01, l=.6, s=.65):
    """
    Get a set of evenly spaced colors in HLS hue space.
    h, l, and s should be between 0 and 1

    Adapted from https://github.com/mwaskom/seaborn/blob/master/seaborn/palettes.py

    Parameters
    ----------
    n_colors : int
        number of colors in the palette
    h : float
        first hue
    l : float
        lightness
    s : float
        saturation

    Returns
    -------
    palette : List-like object of colors as hex color strings.

    """

    hues = linspace(0, 1, int(n_colors) + 1)[:-1]
    hues += h
    hues %= 1
    hues -= hues.astype(int)
    palette = [rgb_to_hex_sep(*hls_to_rgb(h_i, l, s)) for h_i in hues]
    return palette


def assign_colors(color_arr, start=None, end=None, mid='#ffffff', trans=None, categorical_palette=None):

    if categorical_palette is None:
        categorical_palette = None
    
    # continuous palette
    if check_numeric(color_arr):
        if (start is not None) and (end is not None):
            return color_gradient(color_arr, start_hex=start, end_hex=end, mid_hex=mid, trans=trans)
        else:
            raise ValueError('Values for `start` and `end` must be supplied for numeric arrays.')

    # categorical palette
    value_set = set(color_arr)
    n_colors = len(value_set)
    palette_length = len(categorical_palette)

    if n_colors <= palette_length:
        color_dict = dict(zip(value_set, categorical_palette[:n_colors]))
    else:
        val_count_dict = dict()
        for val in color_arr:
            if val in val_count_dict.keys():
                val_count_dict[val] += 1
            else:
                val_count_dict[val] = 1
        color_dict = dict()
        n = 0
        for val, num in sorted(val_count_dict.items(), reverse=True):
            color_dict[val] = categorical_palette[n]
            if n < (palette_length - 1):
                n += 1

    return [color_dict[v] for v in color_arr]
