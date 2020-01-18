from bokeh.models import CheckboxGroup, CheckboxButtonGroup, RangeSlider, Slider, Dropdown, RadioButtonGroup, Button
from bokeh.models import CustomJS
from bokeh.events import ButtonClick
from bokeh.models import markers, WMTSTileSource
from bokeh.models.glyphs import MultiPolygons, Text
from bokeh.models import Plot, Rect, ColumnDataSource

from .color_utils import check_color, check_numeric, color_gradient, hls_palette, order_records

# non-Google-Map map tile sources
# adapted from https://github.com/holoviz/holoviews/blob/master/holoviews/element/tiles.py


def get_tile_source(name):
    tiles = {
        # CartoDB basemaps
        'carto_dark': 'https://cartodb-basemaps-4.global.ssl.fastly.net/dark_all/{Z}/{X}/{Y}.png',
        'carto_eco': 'https://3.api.cartocdn.com/base-eco/{Z}/{X}/{Y}.png',
        'carto_light': 'https://cartodb-basemaps-4.global.ssl.fastly.net/light_all/{Z}/{X}/{Y}.png',
        'carto_midnight': 'https://3.api.cartocdn.com/base-midnight/{Z}/{X}/{Y}.png',

        # Stamen basemaps
        'stamen_terrain': 'https://tile.stamen.com/terrain/{Z}/{X}/{Y}.png',
        'stamen_terrain_retina':  'https://tile.stamen.com/terrain/{Z}/{X}/{Y}@2x.png',
        'stame_watercolor': 'https://tile.stamen.com/watercolor/{Z}/{X}/{Y}.jpg',
        'stamen_toner': 'https://tile.stamen.com/toner/{Z}/{X}/{Y}.png',
        'stamen_toner_background': 'https://tile.stamen.com/toner-background/{Z}/{X}/{Y}.png',
        'stamen_toner_labels': 'https://tile.stamen.com/toner-labels/{Z}/{X}/{Y}.png',

        # Esri maps (see https://server.arcgisonline.com/arcgis/rest/services for the full list)
        'esri_imagery': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{Z}/{Y}/{X}.jpg',
        'esri_natgeo': 'https://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{Z}/{Y}/{X}',
        'esri_usatopo': 'https://server.arcgisonline.com/ArcGIS/rest/services/USA_Topo_Maps/MapServer/tile/{Z}/{Y}/{X}',
        'esri_terrain': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Terrain_Base/MapServer/tile/{Z}/{Y}/{X}',
        'esri_reference': 'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Reference_Overlay/MapServer/tile/{Z}/{Y}/{X}',

        # Miscellaneous
        'osm': 'https://c.tile.openstreetmap.org/{Z}/{X}/{Y}.png',
        'osm_bw': 'https://tiles.wmflabs.org/bw-mapnik/{z}/{x}/{y}.png',
        'wikipedia': 'https://maps.wikimedia.org/osm-intl/{Z}/{X}/{Y}@2x.png'
    }

    if name is None:
        return list(tiles.keys())

    if name not in tiles:
        return None

    return WMTSTileSource(url=tiles[name])


# all supported models
MODELS = {k: getattr(markers, k) for k in markers.__all__}
MODELS['MultiPolygons'] = MultiPolygons
MODELS['Text'] = Text

MODELS_REVERSE = {v: k for k, v in MODELS.items()}

# all supported widgets
WIDGETS = {
    'Dropdown': Dropdown, 
    'RangeSlider': RangeSlider, 
    'CheckboxGroup': CheckboxGroup, 
    'CheckboxButtonGroup': CheckboxButtonGroup,
    'Slider': Slider,
    'RadioButtonGroup': RadioButtonGroup
}

DEFAULT_KWARGS = {
    'CheckboxGroup': {
        'labels': 'auto',
        'active': 'auto',
        'width': 90
    },
    'RangeSlider': {
        'start': 'auto',
        'end': 'auto',
        'step': 1,
        'value': 'auto',
        'width': 50,
        'show_value': True,
        'orientation':
        'vertical',
        'tooltips': False,
        'format': '0'
    },
    'Dropdown': {
        'menu': 'auto',
        'value': 'auto',
        'width': 100,
        'label': 'geohashes'
    },
    'Slider': {
        'start': 'auto',
        'end': 'auto',
        'step': 1,
        'value': 'auto',
        'width': 50,
        'show_value': True,
        'orientation': 'vertical',
        'tooltips': False,
        'format': '0'
    },
    'CheckboxButtonGroup': {
        'labels': 'auto',
        'active': 'auto'
    },
    'RadioButtonGroup': {
        'labels': 'auto',
        'active': 'auto'
    }
}

# filter boilerplate
FILTERS = {
    'Dropdown': '''
        var indices = [];
        for (var i = 0; i <= source.data[reference].length; i++){
            if (source.data[reference][i] == widget.value) {
                indices.push(i)
            }
        }
        return indices;
    ''',
    'Slider': '''
        var indices = [];
        if (widget.step % 1 === 0){
            var value = Math.trunc(widget.value)
        } else {
            var value = widget.value
        }
        
        for (var i = 0; i <= source.data[reference].length; i++){
            if (source.data[reference][i] == widget.value) {
                indices.push(i)
            }
        }
        return indices;
    ''',
    'RangeSlider': '''
        var indices = [];
        if (widget.step % 1 === 0){
            var lower = Math.trunc(widget.value[0])
            var upper = Math.trunc(widget.value[1])
        } else {
            var lower = widget.value[0]
            var upper = widget.value[1]        
        }
        for (var i = 0; i <= source.data[reference].length; i++){
            var value = source.data[reference][i]
            if (value >= lower) {
                if (value <= upper) {
                    indices.push(i)
                }
            }
        }
        return indices;
    ''',
    'CheckboxGroup': '''
        var indices = [];
        var results = [];

        for (var i = 0; i < widget.active.length; i++)
            results.push(widget.labels[widget.active[i]]);

        for (var i = 0; i < source.data[reference].length; i++){
            var value_string = source.data[reference][i].toString()
            if (results.includes(value_string)) {
                indices.push(i)
            }
        }
        return indices;
    ''',
    'CheckboxButtonGroup': '''
        var indices = [];
        var results = [];

        for (var i = 0; i < widget.active.length; i++)
            results.push(widget.labels[widget.active[i]]);

        for (var i = 0; i < source.data[reference].length; i++){
            var value_string = source.data[reference][i].toString()
            if (results.includes(value_string)) {
                indices.push(i)
            }
        }
        return indices;
    ''',
    'RadioButtonGroup': '''
        var indices = [];
        var results = [];

        var result = widget.labels[widget.active];

        for (var i = 0; i < source.data[reference].length; i++){
            var value_string = source.data[reference][i].toString()
            if (result == value_string) {
                indices.push(i)
            }
        }
        return indices;
    '''
}


def auto_advance(slider, ms_delay=500):
    return CustomJS(args=dict(slider=slider), code="""

            function sleep(ms) {
                return new Promise(resolve => setTimeout(resolve, ms));
            }

            async function autoAdvance() {

                slider.value = slider.start;

                while (slider.value < slider.end) {
                    await sleep(%d)
                    slider.value = slider.value + slider.step
                };
            }

            autoAdvance();
        """ % ms_delay
                    )


def auto_widget_kwarg(widget_type, kwarg, reference_array):
    """
    For a particular widget type, keyword argument, and array
    of values, set reasonable defaults.
    
    """
    
    if widget_type in ("CheckboxGroup", "CheckboxButtonGroup"):
        reference_set = list(set(reference_array))
        if kwarg == 'labels':
            return reference_set
        if kwarg == 'active':
            return [x for x in range(len(reference_set))]
        raise ValueError(
            'The only auto-populating kwargs for {} are `labels` and `active`.'.format(widget_type)
        )
    if widget_type == "RangeSlider":
        if kwarg == 'start':
            return min(reference_array)
        if kwarg == 'end':
            return max(reference_array)
        if kwarg == 'value':
            return min(reference_array), max(reference_array)
        raise ValueError(
            'The only auto-populating kwargs for {} are `start`, `end` and `value`.'.format(widget_type)
        ) 
    if widget_type == "Slider":
        if kwarg == 'start':
            return min(reference_array)
        if kwarg == 'end':
            return max(reference_array)
        if kwarg == 'value':
            return min(reference_array)
        raise ValueError(
            'The only auto-populating kwargs for {} are `start`, `end` and `value`.'.format(widget_type)
        )
    if widget_type == "Dropdown":
        reference_set = list(set(reference_array))
        if kwarg == 'menu':
            return reference_set
        if kwarg == 'value':
            return reference_set[0]
        raise ValueError(
            'The only auto-populating kwargs for {} are `menu` and `value`.'.format(widget_type)
        )    
    if widget_type in ("RadioButtonGroup", ):
        reference_set = list(set(reference_array))
        if kwarg == 'labels':
            return reference_set
        if kwarg == 'active':
            return 0
        raise ValueError(
            'The only auto-populating kwargs for {} are `labels` and `active`.'.format(widget_type)
        )
    
    raise NotImplementedError('Widget type `{}` not yet implemented.'.format(widget_type))

    
def prepare_properties(
    bokeh_model, kwargs, source_df, bar_height,
    start_hex='#ff0000', end_hex='#0000ff', mid_hex='#ffffff', color_transform=None
):
    """
    For a particular Bokeh model and accompanying keyword arguents,
    automatically set color and alpha values.
    
    """

    colorbar = None

    hover_kwargs = dict()
    for k, v in kwargs.items():
        if k.startswith('hover_'):
            hover_kwargs[k.replace('hover_', '')] = v

    for k in hover_kwargs.keys():
        _ = kwargs.pop('hover_' + k)

    if 'color' in kwargs.keys():
        color = kwargs.pop('color')
        for v in bokeh_model.dataspecs():
            if 'color' in v:
                kwargs[v] = color

    color_keys = [key for key in bokeh_model.dataspecs() if ('color' in key) and (key in kwargs.keys())]

    new_fields = dict()
    for key in color_keys:
        color_val = kwargs[key]

        if color_val is None:
            continue

        if isinstance(color_val, str):
            if check_color(color_val):
                continue
            else:
                color_arr = source_df[color_val].tolist()
                in_datasource = True
        else:
            color_arr = color_val
            in_datasource = False

        if not all(check_color(c) for c in color_arr):

            if check_numeric(color_arr):
                if (start_hex is not None) and (end_hex is not None):
                    color_new = color_gradient(
                        color_arr,
                        start_hex=start_hex, end_hex=end_hex, mid_hex=mid_hex,
                        trans=color_transform
                    )

                    colorbar = make_colorbar(color_arr, color_new, bar_height)
                else:
                    raise ValueError('Values for `start_hex` and `end_hex` must be supplied for numeric arrays.')
            else:
                n_colors = len(set(color_arr))
                color_df = source_df.groupby(color_arr)[['x_coord_point', 'y_coord_point']].mean()
                score = order_records(color_df['x_coord_point'].tolist(), source_df['y_coord_point'].tolist())
                palette = hls_palette(n_colors, h=0.5, l=0.5, s=1.0)
                color_dict = dict(zip(color_df.index.tolist(), [palette[ind] for ind in score]))
                color_new = [color_dict[ind] for ind in color_arr]

            if in_datasource:
                new_val = '{}_autocolor'.format(color_val)
                new_fields[new_val] = color_new
                kwargs[key] = new_val
            else:
                kwargs[key] = color_new

    if 'alpha' in kwargs.keys():
        alpha = kwargs.pop('alpha')
        for v in bokeh_model.dataspecs():
            if 'alpha' in v:
                kwargs[v] = alpha
                    
    return kwargs, hover_kwargs, new_fields, colorbar


def make_colorbar(values, colors, bar_height):
    val_list = list()
    seen = set()
    for val, color in zip(values, colors):
        if color not in seen:
            val_list.append((val, color))
            seen.add(color)

    val_opts, color_opts = zip(*sorted(val_list))
    n_opts = len(val_opts)
    longest_val = len(max([str(v) for v in val_opts], key=len))
    opt_inds = [v for v in range(n_opts)]
    max_color, max_val, max_ind = color_opts[0], val_opts[0], opt_inds[0]
    min_color, min_val, min_ind = color_opts[-1], val_opts[-1], opt_inds[-1]

    colorbar = Plot(
        frame_width=10 * longest_val, frame_height=bar_height,
        title=None, min_border=0,
        toolbar_location=None, outline_line_color=None
    )
    colorbar_source = ColumnDataSource({'x': [0] * n_opts, 'y': opt_inds, 'vals': val_opts, 'colors': color_opts})
    glyph = Rect(x=1, y="y", width=1, height=1, fill_color="colors", line_color=None)
    text_source = ColumnDataSource({'x': [1, 1], 'y': [min_ind + 1, max_ind - 1], 'text': [str(min_val), str(max_val)]})
    text = Text(x=1, y='y', text='text', text_font_size='10pt', text_align='center', text_baseline='middle')
    colorbar.add_glyph(colorbar_source, glyph)
    colorbar.add_glyph(text_source, text)

    return colorbar
