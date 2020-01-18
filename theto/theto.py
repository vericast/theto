from bokeh.io import output_notebook, show, save
from bokeh.models.glyphs import Quadratic, Segment
from bokeh.models import GMapPlot, GMapOptions, ColumnDataSource, Range1d, Plot
from bokeh.models.tools import HoverTool, WheelZoomTool, ResetTool, PanTool, TapTool
from bokeh.models.annotations import Title, Legend, LegendItem
from bokeh.resources import CDN
from bokeh.models.layouts import Row, Column, WidgetBox
from bokeh.models import CustomJS, CustomJSFilter, CDSView, OpenURL
from bokeh.models import DataTable, TableColumn
from bokeh.models import LinearAxis, MercatorTicker, MercatorTickFormatter

from os import path
from pandas import DataFrame
from numpy import array

from . import bokeh_utils, coordinate_utils, gmaps_utils


class WorkflowOrderError(Exception):
    pass


def flatten(items, seqtypes=(list, tuple)):
    for i, x in enumerate(items):
        while i < len(items) and isinstance(items[i], seqtypes):
            items[i:i+1] = items[i]
    return items


class Theto(object):
    """
    This class provides a wrapper to produce most of the boilerplate needed to use Bokeh to plot on 
    top of Google Maps or other tile images.
    
    Example usage:
    
    geohashes = [
        'dnrgrfm', 'dnrgrf3', 'dnrgrf7', 'dnrgrf5', 'dnrgrfk', 'dnrgrf1', 
        'dnrgrfh', 'dnrgrf2', 'dnrgrcu', 'dnrgrfj', 'dnrgrcv', 'dnrgrf4'
    ]
    
    API_KEY = (GET API KEY AT developers.google.com/maps/documentation/javascript/get-api-key)
    
    (
        Theto(api_key=API_KEY)
        .add_source(geohashes, label='a', order=range(len(geohashes)))
        .prepare_plot(plot_width=700)
        .add_layer('a', Patches, color='yellow', alpha=0.5)
        .add_layer('a', Circle, color='blue', size=20, alpha=0.75)
        .add_layer(
            'a', Text, text='order', text_color='white', text_font_size='10pt', text_align='center',
            text_baseline='middle'
        )
        .render_plot('auto')
    )
    """
    
    def __init__(self, api_key=None, precision=6, autohide=True, padding=0.05):
        """
        Instantiate the class.
        
        Parameters
        
        api_key (str): A Google Maps API key, which can be obtained at
            developers.google.com/maps/documentation/javascript/get-api-key.
            If None, only non-Google tile providers ('osm', 'esri', 
            'wikipedia', 'cartodb') will be available.

        precision (int): The number of decimals places that are meaningful for
            the plot. Defaults to 6, which is about as precise as phone's
            GPS signal can be expected to be. This precision will get automatically
            transformed in cases where latitude and longitude are projected
            to web Mercator maps.

        autohide (bool): if True, the toolbar on plots will be hidden unless the
            mouse is hovering over the plot itself.

        padding (float): the minimum amount of space that should exist between the
            plotted objects and the edge of the map, expressed as a percentage
            of the range of the relevant direction. So a padding factor of 0.05 (the
            default) will multiply the factor by the maximum latitude minus the minimum
            latitude and add that amount to the top and bottom edges of the graph, and
            then multiply the factor by the maximum longitude minus the minimum
            longitdue and add that amount to the right and left edges of the graph.
        
        """
        self.api_key = api_key
        self.precision = precision
        self.autohide = autohide
        self.padding = padding
        self.colorbar = None

        # removed 'x_coord_point', 'y_coord_point', 'raw_data'
        self.omit_columns = [
            'index', 'x_coords', 'y_coords', 'x_coords_transform', 'y_coords_transform',
            'x_coord_point_transform', 'y_coord_point_transform'
        ]

        self.sources = dict()
        self.columndatasources = dict()
        self.views = dict()
        self.widgets = dict()
        self.data_tables = list()
        self.custom_js = None
        self.xmin = None
        self.ymin = None
        self.xmax = None
        self.ymax = None
        self.plot = None
        self.legend = Legend(location='bottom_center', click_policy='hide', background_fill_color='#fafafa')
        self.validation = {
            'add_source': False,
            'add_widget': False,
            'prepare_plot': False,
            'add_layer': False,
            'render_plot': False
        }
        self.remove_columns = dict()
        
    def _validate_workflow(self, stage):
        """
        Checks the input stage against previously executed stages and raises
        an error if things have been done out of order.
        
        """
        
        if stage == 'add_source':
            if self.validation['add_widget']:
                raise WorkflowOrderError('New sources cannot be added after `add_widget` has been called.')
            if self.validation['prepare_plot']:
                raise WorkflowOrderError('New sources cannot be added after `prepare_plot` has been called.')
            if self.validation['add_layer']:
                raise WorkflowOrderError('New sources cannot be added after `add_layer` has been called.')
            if self.validation['render_plot']:
                raise WorkflowOrderError('Method `render_plot` has already been called. Start new workflow.')
        if stage == 'add_widget':
            if not self.validation['add_source']:
                raise WorkflowOrderError('Method `add_source` must be called before adding a widget.')
            if self.validation['prepare_plot']:
                raise WorkflowOrderError('New widgets cannot be added after `prepare_plot` has been called.')
            if self.validation['add_layer']:
                raise WorkflowOrderError('New widgets cannot be added after `add_layer` has been called.')
            if self.validation['render_plot']:
                raise WorkflowOrderError('Method `render_plot` has already been called. Start new workflow.')
        if stage == 'prepare_plot':
            if not self.validation['add_source']:
                raise WorkflowOrderError('Method `add_source` must be called before calling `prepare_plot`.')
            if self.validation['add_layer']:
                raise WorkflowOrderError('Plot cannot be prepared after `add_layer` has been called.')
            if self.validation['render_plot']:
                raise WorkflowOrderError('Method `render_plot` has already been called. Start new workflow.')
        if stage == 'add_layer':
            if not self.validation['add_source']:
                raise WorkflowOrderError('Method `add_source` must be called before adding a layer.')
            if not self.validation['prepare_plot']:
                raise WorkflowOrderError('New layers cannot be added after `prepare_plot` has been called.')
            if self.validation['render_plot']:
                raise WorkflowOrderError('Method `render_plot` has already been called. Start new workflow.')
        if stage == 'render_plot':
            if not self.validation['add_source']:
                raise WorkflowOrderError('Method `add_source` must be called before rendering the plot.')
            if not self.validation['prepare_plot']:
                raise WorkflowOrderError('Method `prepare_plot` must be called before rendering the plot.')
            if not self.validation['add_layer']:
                raise WorkflowOrderError('Method `add_layer` must be called before rendering the plot.')
        if stage == 'add_path':
            if not self.validation['add_source']:
                raise WorkflowOrderError('Method `add_source` must be called before adding a path.')
            if not self.validation['prepare_plot']:
                raise WorkflowOrderError('Method `prepare_plot` must be called before adding a path.')
            if self.validation['render_plot']:
                raise WorkflowOrderError('Method `render_plot` has already been called. Start new workflow.')
            if self.validation['add_widget']:
                raise WorkflowOrderError('Plot contains widgets, which are not compatible with paths.')
        if stage == 'add_data_table':
            if not self.validation['add_source']:
                raise WorkflowOrderError('Method `add_source` must be called before adding a data table.')
            if not self.validation['prepare_plot']:
                raise WorkflowOrderError('Method `prepare_plot` must be called before adding a data table.')
            if self.validation['render_plot']:
                raise WorkflowOrderError('Method `render_plot` has already been called. Start new workflow.')

    def _set_coordinate_bounds(self, df):
        """
        Given a new source DataFrame, set or update 
        coordinate bounds for the plot.
        
        """

        x_coords = flatten(df['x_coords'].tolist())
        y_coords = flatten(df['y_coords'].tolist())

        xmin = min(x_coords)
        xmax = max(x_coords)
        ymin = min(y_coords)
        ymax = max(y_coords)
        
        if self.xmin is not None:
            if xmin < self.xmin:
                self.xmin = xmin
        else:
            self.xmin = xmin

        if self.xmax is not None:
            if xmax > self.xmax:
                self.xmax = xmax
        else: 
            self.xmax = xmax

        if self.ymin is not None:
            if ymin < self.ymin:
                self.ymin = ymin
        else:
            self.ymin = ymin

        if self.ymax is not None:
            if ymax > self.ymax:
                self.ymax = ymax
        else:
            self.ymax = ymax

    def add_source(self, data, label, uid=None, column_name=None, **kwargs):
        """
        Add a source to the `self.sources`, to be used in the plot.
        
        Parameters:
        
        data (list or DataFrame): a list of geohashes, shapely objects, well-known text 
            strings, or longitude/latitude pairs; or a DataFrame where the objects to be 
            plotted are indicated by `column_name`
        label (str): a name that can be used to reference the source going forward
        uid (str or list): a list of unique ids (necessary for pathing); if None, `range` 
            is used to assign a number. If None, either `data` (if data is a list) or 
            `data[column_name]` (if data is a DataFrame) will be used.
        column_name (str): optional, the column of `data` that contains geohashes, shapely 
            objects, well-known text strings, or longitude/latitude pairs
        kwargs: lists of the same length as `data` if `data` is a list. These will be 
            appended to the data as metadata
        
        """
        
        self._validate_workflow('add_source')

        # process data into x and y coordinates
        if type(data) == DataFrame:
            if column_name is None:
                raise ValueError('If data is a dataframe then column_name must be specified.')
            df = data.copy()
            raw_data = df[column_name].values.tolist()
        else:
            raw_data = list(data)
            df = DataFrame(index=range(len(raw_data)))
            column_name = 'raw_data'

        if all(coordinate_utils.detect_geojson(v) for v in raw_data):
            processed_data = [coordinate_utils.import_geojson(v, self.precision) for v in raw_data]
        else:
            processed_data = [coordinate_utils.process_input_value(v) for v in raw_data]

        processed_data_transformed = [coordinate_utils.to_webmercator(v) for v in processed_data]
        buf = 1 / (10 ** self.precision)

        # original projection
        x_coords_shape, y_coords_shape = zip(*[coordinate_utils.shape_to_nested_list(v, buf) for v in processed_data])
        df['x_coords'], df['y_coords'] = list(x_coords_shape), list(y_coords_shape)

        x_coords_point, y_coords_point = zip(*[list(*v.representative_point().coords) for v in processed_data])
        df['x_coord_point'] = [round(v, self.precision) for v in x_coords_point]
        df['y_coord_point'] = [round(v, self.precision) for v in y_coords_point]

        # webmercator projection
        x_coords_shape, y_coords_shape = zip(*[
            coordinate_utils.shape_to_nested_list(v, buf) for v in processed_data_transformed
        ])
        df['x_coords_transform'], df['y_coords_transform'] = list(x_coords_shape), list(y_coords_shape)

        x_coords_point, y_coords_point = zip(*[
            list(*v.representative_point().coords) for v in processed_data_transformed
        ])
        df['x_coord_point_transform'] = [round(v, self.precision) for v in x_coords_point]
        df['y_coord_point_transform'] = [round(v, self.precision) for v in y_coords_point]

        if len(kwargs) > 0:
            for k, v in kwargs.items():
                df[k] = v

        self._set_coordinate_bounds(df)

        df[column_name] = [coordinate_utils.dumps_if_shapely(ob) for ob in raw_data]

        if uid is None:
            df['uid'] = range(df.shape[0])
        elif type(uid) is str:
            df['uid'] = df[uid]
        else:
            df['uid'] = uid
            
        self.sources[label] = df.copy()
        self.remove_columns[label] = ['f', 'p']
        self.validation['add_source'] = True
        
        return self

    def add_widget(self, source_label, widget_type, reference, widget_name=None, custom_js=None, **kwargs):
        """
        Add widgets to subset the data displayed in the plot.
        
        Parameters:
            source_label (str): the label for the data source to be used for the widget
            widget_type (str): a widget that is a valid key from
                `bokeh_utils.WIDGETS`.
            widget_name (str): an arbitrary name that can be used to identify the widget
                (necessary if `custom_js` is not None).
            reference (str): a column name from `self.sources[source_label]` that the widget
                should look at to filter the data source
            custom_js (str): custom javascript code for defining the filtering fuunction
            kwargs: all keyword arguments will be fed the instantiation of the widget to define
                the look and content of the interaction (ranges, initial values, etc.)
        
        """

        self._validate_workflow('add_widget')

        if widget_type == 'Animation':
            widget_type = 'Slider'
            animate = True
        else:
            animate = False

        if widget_name is None:
            widget_name = widget_type
        
        if reference not in self.sources[source_label].columns:
            raise ValueError("Reference '{}' not in data source '{}'.".format(reference, source_label))
                
        source = self.sources[source_label]
        
        ref_array = source[reference].tolist()

        animation_kwargs = {'button_type': 'primary', 'label': 'Start', 'ms_delay': 500}
        remove_kw = list()

        for k, v in kwargs.items():
            if k.startswith('animation'):
                remove_kw.append(k)
                k = k.replace('animation_', '')
                animation_kwargs[k] = v

        for k in remove_kw:
            _ = kwargs.pop(k)

        for k, v in bokeh_utils.DEFAULT_KWARGS[widget_type].items():
            if k not in kwargs:
                kwargs[k] = v

        widget = bokeh_utils.WIDGETS[widget_type](name=widget_name, **{
            k: v if v != 'auto' else bokeh_utils.auto_widget_kwarg(widget_type, k, ref_array)
            for k, v in kwargs.items()
        })

        # This callback is crucial to trigger changes when the widget changes
        callback = CustomJS(args=dict(source=None), code="""
            source.change.emit();
            console.log()
        """)
        use_active = widget_type in ('CheckboxButtonGroup', 'CheckboxGroup', 'RadioButtonGroup')
        widget.js_on_change('active' if use_active else 'value', callback)
        
        if custom_js is None:
            if self.custom_js is not None:
                raise ValueError('Either all widgets or no widgets must use custom_js.')
                
            if source_label in self.views:
                raise ValueError('Multiple widgets can only be used with custom_js.')
                
            js_filter = CustomJSFilter(
                args=dict(widget=widget, reference=reference), 
                code=bokeh_utils.FILTERS[widget_type]
            )
            
        else:
            if self.custom_js is None:
                self.custom_js = CustomJSFilter(args={}, code=custom_js)
                
            js_filter = self.custom_js
            js_filter.args.update({widget_name: widget, widget_name + '_ref': reference})

        self.widgets[widget_name] = {'widget': widget, 'filter': js_filter, 'source': source_label}

        if animate:
            ms_delay = animation_kwargs.pop('ms_delay')
            button = bokeh_utils.Button(**animation_kwargs)
            button.js_on_event(bokeh_utils.ButtonClick, bokeh_utils.auto_advance(widget, ms_delay))
            self.widgets['animation'] = {'widget': button, 'filter': None, 'source': None}

        if source_label not in self.views:
            self.views[source_label] = CDSView(filters=[js_filter])
            
        self.validation['add_widget'] = True
        
        return self

    def _create_columndatasource(self, source_df):
        """
        Convert a source DataFrame into a Bokeh ColumnDataSource
        based on what type of plot has been chosen.
        
        """
        
        suffix = '_transform' if type(self.plot) != GMapPlot else ''
        x_coords_label = 'x_coords{}'.format(suffix)
        y_coords_label = 'y_coords{}'.format(suffix)
        x_point_label = 'x_coord_point{}'.format(suffix)
        y_point_label = 'y_coord_point{}'.format(suffix)

        xsf = source_df[x_coords_label].tolist()
        ysf = source_df[y_coords_label].tolist()

        xsp = source_df[x_point_label].tolist()
        ysp = source_df[y_point_label].tolist()
        
        omit = [c for c in self.omit_columns if c in source_df.columns]
        source = ColumnDataSource(source_df.drop(omit, axis=1).to_dict('list'))
        source.data['xsf'] = xsf
        source.data['ysf'] = ysf
        source.data['xsp'] = xsp
        source.data['ysp'] = ysp
        
        return source
    
    def prepare_plot(
        self, plot_width=700, plot_height=None, zoom=None, map_type='carto_light',
        title=None, **kwargs
    ):
        """
        Create the actual plot object (stored in `self.plot`).
        
        Parameters:
        
        plot_width (int): desired plot width, in pixels
        plot_height (int): desired plot height, will be calculated 
            automatically if not supplied
        zoom (int): zoom factor for Google Maps, will be calculated 
            automatically if not supplied
        map_type (string): 'satellite', 'roadmap', or 'hybrid'
        title (string or tuple): if string, title is added to plot; 
            if tuple, the first value is the title, and second value 
            is a dict of kwargs
        kwargs: any options passed to Bokeh GMapPlot (title, etc.)
        
        """
        
        self._validate_workflow('prepare_plot')
        
        zoom_level, lat_center, lng_center, auto_plot_height = gmaps_utils.estimate_zoom(
            plot_width,
            x_bounds=(self.xmin, self.xmax),
            y_bounds=(self.ymin, self.ymax)
        )
        if plot_height is None:
            plot_height = auto_plot_height
            
        if zoom is None:
            zoom = zoom_level
        
        if title is not None:
            if isinstance(title, str):
                title = Title(text=title)
            if isinstance(title, (list, tuple)):
                title, title_kwargs = title
                title = Title(text=title, **title_kwargs)
                
        if map_type in ('satellite', 'roadmap', 'terrain', 'hybrid'):
            if self.api_key is None:
                raise ValueError(
                    'Class must be instantiated with Google Maps API key to use map_type `{}`'.format(map_type)
                )

            map_options = GMapOptions(lat=lat_center, lng=lng_center, map_type=map_type, zoom=zoom)
            self.plot = GMapPlot(
                x_range=Range1d(),
                y_range=Range1d(),
                map_options=map_options,
                plot_width=plot_width,
                plot_height=plot_height,
                title=title,
                **kwargs
            )
            self.plot.api_key = self.api_key
            self.plot.add_tools(WheelZoomTool(), ResetTool(), PanTool(), TapTool())
        elif map_type in bokeh_utils.get_tile_source(None):
            x_rng, y_rng = self.xmax - self.xmin, self.ymax - self.ymin
            x_range = Range1d(
                start=coordinate_utils.coord_to_webmercator(
                    self.xmin - (x_rng * self.padding),
                    precision=self.precision, 
                    longitude=True
                ), 
                end=coordinate_utils.coord_to_webmercator(
                    self.xmax + (x_rng * self.padding),
                    precision=self.precision,
                    longitude=True
                )
            )
            y_range = Range1d(
                start=coordinate_utils.coord_to_webmercator(
                    self.ymin - (y_rng * self.padding),
                    precision=self.precision,
                    longitude=False
                ), 
                end=coordinate_utils.coord_to_webmercator(
                    self.ymax + (y_rng * self.padding),
                    precision=self.precision,
                    longitude=False
                )
            )
            self.plot = Plot(
                x_range=x_range,
                y_range=y_range,
                frame_width=plot_width,
                frame_height=plot_height,
                title=title,
                **kwargs
            )
            
            self.plot.add_tile(bokeh_utils.get_tile_source(map_type))
            self.plot.add_tools(WheelZoomTool(), ResetTool(), PanTool(), TapTool())

            xformatter = MercatorTickFormatter(dimension="lon")
            xticker = MercatorTicker(dimension="lon")
            xaxis = LinearAxis(
                formatter=xformatter, ticker=xticker,
                axis_line_alpha=0.1, minor_tick_line_alpha=0.1, major_tick_line_alpha=0.1, major_label_text_alpha=0.5
            )
            self.plot.add_layout(xaxis, 'below')

            yformatter = MercatorTickFormatter(dimension="lat")
            yticker = MercatorTicker(dimension="lat")
            yaxis = LinearAxis(
                formatter=yformatter, ticker=yticker,
                axis_line_alpha=0.1, minor_tick_line_alpha=0.1, major_tick_line_alpha=0.1, major_label_text_alpha=0.5
            )
            self.plot.add_layout(yaxis, 'left')

        else:
            raise ValueError('Invalid map_type.')
                    
        for source_label, source in self.sources.items():
            source = self._create_columndatasource(source)
            
            for widget_name in self.widgets.keys():
                widget_dict = self.widgets[widget_name]
                if widget_dict['source'] == source_label:
                    widget_dict['filter'].args['source'] = source
                    for callback_list in widget_dict['widget'].js_property_callbacks.values():
                        for callback in callback_list:
                            callback.args['source'] = source
                    
            if source_label in self.views:
                self.views[source_label].source = source
                
            self.columndatasources[source_label] = source
            
        self.validation['prepare_plot'] = True
        
        return self
        
    def add_layer(
        self, source_label, bokeh_model='MultiPolygons', tooltips=None, legend=None, click_for_map=None,
        start_hex='#ff0000', end_hex='#0000ff', mid_hex='#ffffff', color_transform=None,
        **kwargs
    ):
        """
        Add bokeh models (glyphs or markers) to `self.plot`. 
        `self.prepare_plot` must have been called previous to this.
        
        Parameters:
        
        source_label (str): string corresponding to a label previously 
            called in `self.add_source`
        bokeh_model: any Bokeh model or glyph class
        tooltips: string or list of tuples (passed to Bokeh HoverTool)
        legend (str): name to assign to this layer in the plot legend
        start_hex (str): the color with which to start a color gradient
        end_hex (str): the color with which to end a color gradient
        mid_hex (str): the color to use for zero in a color gradient if 
            the basis of that gradient contains both positive and negative 
            values
        color_transform (callable): any function that can transform a 
            numpy array (log, log10, etc.)
        kwargs: options passed to the objected for `bokeh_model`
        
        This method allows two special kwargs: 'color' and 'alpha'. When 
        used with a bokeh model that has 'fill_color' and 'line_color' and 
        'fill_alpha' and 'line_alpha' properties, calling the special kwarg 
        will use the same value for both.
        
        """
    
        self._validate_workflow('add_layer')
        
        if self.plot is None:
            raise AssertionError('self.plot is null; call `self.prepare_plot`.')

        if bokeh_model not in bokeh_utils.MODELS:
            raise ValueError(
                'Valid values for `bokeh_model` are: {}'.format(
                    ', '.join([repr(x) for x in bokeh_utils.MODELS.keys()])
                )
            )
            
        bokeh_model = bokeh_utils.MODELS[bokeh_model]
        kwargs, hover_kwargs, new_fields, colorbar = bokeh_utils.prepare_properties(
            bokeh_model, kwargs, self.sources[source_label], bar_height=self.plot.frame_height,
            start_hex=start_hex, end_hex=end_hex, mid_hex=mid_hex,
            color_transform=color_transform,
        )

        if self.colorbar is None:
            self.colorbar = colorbar
                
        source = self.columndatasources[source_label]

        for k, v in new_fields.items():
            self.columndatasources[source_label].data[k] = v

        hover_object = None
        if bokeh_model == bokeh_utils.MODELS['MultiPolygons']:
            if type(self.plot) == GMapPlot:
                raise ValueError(
                        'The `MultiPolygon` glyph cannot yet be used with a Google Maps plot.'
                    )
            model_object = bokeh_model(xs='xsf', ys='ysf', name=source_label, **kwargs)

            if len(hover_kwargs) > 0:
                for k, v in hover_kwargs.items():
                    kwargs[k] = v
                hover_object = bokeh_model(xs='xsf', ys='ysf', name=source_label, **kwargs)

            if 'f' in self.remove_columns[source_label]:
                _ = self.remove_columns[source_label].pop(self.remove_columns[source_label].index('f'))

        else:

            model_object = bokeh_model(x='xsp', y='ysp', name=source_label, **kwargs)

            if len(hover_kwargs) > 0:
                for k, v in hover_kwargs:
                    kwargs[k] = v
                hover_object = bokeh_model(xs='xsf', ys='ysf', name=source_label, **kwargs)

            if 'p' in self.remove_columns[source_label]:
                _ = self.remove_columns[source_label].pop(self.remove_columns[source_label].index('p'))

        if source_label in self.views:
            if len(hover_kwargs) > 0:
                rend = self.plot.add_glyph(
                    source, model_object, hover_glyph=hover_object, view=self.views[source_label]
                )
            else:
                rend = self.plot.add_glyph(source, model_object, view=self.views[source_label])
        else:
            if len(hover_kwargs) > 0:
                rend = self.plot.add_glyph(source, model_object, hover_glyph=hover_object)
            else:
                rend = self.plot.add_glyph(source, model_object)

        if legend is not None:
            li = LegendItem(label=legend, renderers=[rend])
            self.legend.items.append(li)
    
        if tooltips is not None:
            if tooltips == 'all':
                tooltips = [
                    (k, '@{}'.format(k)) for k in source.data.keys()
                    if k not in ('xsf', 'ysf', 'xsp', 'ysp')
                ]
            elif tooltips == 'point':
                tooltips = [
                    (k, '@{}'.format(k)) for k in source.data.keys()
                    if k not in ('xsf', 'ysf', 'xsp', 'ysp', 'raw_data')
                ]
            elif tooltips == 'raw_data':
                tooltips = [
                    (k, '@{}'.format(k)) for k in source.data.keys()
                    if k not in ('xsf', 'ysf', 'xsp', 'ysp', 'x_coord_point', 'y_coord_point')
                ]
            elif tooltips == 'meta':
                tooltips = [
                    (k, '@{}'.format(k)) for k in source.data.keys()
                    if k not in ('xsf', 'ysf', 'xsp', 'ysp', 'x_coord_point', 'y_coord_point', 'raw_data')
                ]

        self.plot.add_tools(HoverTool(tooltips=tooltips, renderers=[rend]))

        if click_for_map is not None:
            taptool = self.plot.select(type=TapTool)
            if click_for_map == 'google':
                url = 'https://maps.google.com/maps?q=@y_coord_point,@x_coord_point'
                taptool.callback = OpenURL(url=url)
            elif click_for_map == 'bing':
                url = 'https://bing.com/maps/default.aspx?sp=point.'
                url += '@{y_coord_point}_@{x_coord_point}_Selected point&style=r'
                taptool.callback = OpenURL(url=url)
            else:
                raise NotImplementedError('Value for `click_for_map` must be "bing", "google" or None.')

        self.validation['add_layer'] = True
        
        return self

    def add_path(self, source_label, links=None, edge_type='curved', tooltips=None, legend=None, **kwargs):
        """
        Connect all points in the datasource in a path (to show order).
        `self.prepare_plot` must have been called previous to this.
        
        Parameters:
        
        source_label (str): string corresponding to a label previously 
            called in `self.add_source`
        order_col: the column of a data source specifying the order of the records
        tooltips: string or list of tuples (passed to Bokeh HoverTool)
        legend (str): name to assign to this layer in the plot legend
        kwargs: options passed to the objected for `bokeh_model`
        
        This method allows two special kwargs: 'color' and 'alpha'. When 
            used with a bokeh model that has 'fill_color' and 'line_color' 
            and 'fill_alpha' and 'line_alpha' properties, calling the special 
            kwarg will use the same value for both.
        
        """
    
        self._validate_workflow('add_path')
        
        source = self.sources[source_label].copy()
        
        suffix = '_transform' if type(self.plot) != GMapPlot else ''
        x_point_label = 'x_coord_point{}'.format(suffix)
        y_point_label = 'y_coord_point{}'.format(suffix)

        if all(isinstance(x, (int, float)) for x in source[links].tolist()):
            x1 = source.sort_values(links)[x_point_label].values
            y1 = source.sort_values(links)[y_point_label].values
            x2 = x1[1:]
            y2 = y1[1:]
            x1 = x1[:-1]
            y1 = y1[:-1]
            x3 = (x1 + x2) / 2
            y3 = (y1 + y2) / 2
            xc = x3 + abs(y3-y2)
            yc = y3 + abs(x3-x2)

            new_source = {'x1': x1, 'x2': x2, 'xc': xc, 'y1': y1, 'y2': y2, 'yc': yc}

            for c in source.columns:
                if (c not in self.omit_columns) and c not in new_source:
                    new_source[c] = source[c].values[:-1] 
        elif all(isinstance(x, (list, tuple, set)) for x in source[links].tolist()):
            if 'uid' not in source.columns:
                raise ValueError('Source must contain column `uid` when links is a list of iterables.')
                
            nodes = source['uid'].tolist()
            edges = source[links].tolist()
            node_x = source.set_index('uid')[x_point_label].to_dict()
            node_y = source.set_index('uid')[y_point_label].to_dict()

            a_vals, x1, x2, y1, y2 = zip(*[
                (a, node_x[a], node_x[b], node_y[a], node_y[b]) 
                for a, bs in zip(nodes, edges) for b in bs
            ])
            x1, x2, y1, y2 = array(x1), array(x2), array(y1), array(y2)    
            x3 = (x1 + x2) / 2
            y3 = (y1 + y2) / 2
            xc = x3 + abs(y3-y2)
            yc = y3 + abs(x3-x2)

            new_source = {'x1': x1, 'x2': x2, 'xc': xc, 'y1': y1, 'y2': y2, 'yc': yc}
            
            for c in source.columns:
                if (c not in self.omit_columns) and c not in new_source:
                    col_dict = source.set_index('uid', drop=False)[c].to_dict()
                    new_source[c] = [col_dict[v] for v in a_vals]
        else:
            raise ValueError(
                'Values of `links` field must be numeric or a list, set, or tuple of values from the `uid` field.'
            )
        
        if 'color' in kwargs.keys():
            color = kwargs.pop('color')
            for v in Quadratic.dataspecs():
                if 'color' in v:
                    kwargs[v] = color

        if 'alpha' in kwargs.keys():
            alpha = kwargs.pop('alpha')
            for v in Quadratic.dataspecs():
                if 'alpha' in v:
                    kwargs[v] = alpha
                
        if edge_type == 'curved':
            model_object = Quadratic(
                x0='x1', y0='y1', x1="x2", y1="y2", cx="xc", cy="yc", name=source_label, **kwargs
            )
        elif edge_type == 'straight':
            model_object = Segment(
                x0='x1', y0='y1', x1="x2", y1="y2", name=source_label, **kwargs
            )
        else:
            raise ValueError('Keyword `edge_type` must be either "curved" or "straight".')

        source = ColumnDataSource(new_source, name=source_label)
        rend = self.plot.add_glyph(source, model_object)
        
        if legend is not None:
            li = LegendItem(label=legend, renderers=[rend])
            self.legend.items.append(li)
    
        if tooltips is not None:
            self.plot.add_tools(HoverTool(tooltips=tooltips, renderers=[rend]))
            
        return self

    def add_data_table(self, source_label, columns='all', **kwargs):

        self._validate_workflow('add_data_table')

        source = self.columndatasources[source_label]

        if isinstance(columns, (list, tuple)):
            columns = {
                k: max([len(str(val)) for val in v] + [len(k)]) for k, v in source.data.items()
                if k in columns
            }
        else:
            if columns == 'all':
                omit_cols = ('xsf', 'ysf', 'xsp', 'ysp')
            elif columns == 'point':
                omit_cols = ('xsf', 'ysf', 'xsp', 'ysp', 'raw_data')
            elif columns == 'raw_data':
                omit_cols = ('xsf', 'ysf', 'xsp', 'ysp', 'x_coord_point', 'y_coord_point')
            elif columns == 'meta':
                omit_cols = ('xsf', 'ysf', 'xsp', 'ysp', 'x_coord_point', 'y_coord_point', 'raw_data')
            else:
                omit_cols = list()

            columns = {
                k: max([len(str(val)) for val in v] + [len(k)]) for k, v in source.data.items()
                if k not in omit_cols
            }

        default_kw = {
            'editable': False,
            'index_position': None,
            'reorderable': True,
            'scroll_to_selection': True,
            'selectable': 'checkbox',
            'sortable': True,
            'fit_columns': False
        }

        for k, v in default_kw.items():
            if k not in kwargs.keys():
                kwargs[k] = v

        data_table = DataTable(
            source=source,
            columns=[TableColumn(field=k, title=k, width=v * 8) for k, v in columns.items()],
            **kwargs
        )

        self.data_tables.append(data_table)

        return self
            
    def render_plot(
        self, display_type='object', directory=None, legend_position='below', 
        legend_orientation='horizontal', widget_position='left'
    ):
        """
        Pull everything together into a plot ready for display.
        
        Parameters:
        
        display_plot (str): either 'object', 'notebook', or an 
            arbitrary string. If 'object', it returns the plot object. 
            If 'notebook', the plot is displayed in the notebok. 
            If an arbitrary string that does not match one of the other pptions, 
            the plot is saved to '{display_plot}.html' in the current working 
            directory if `directory` is None, or in `directory` if not None.
            
        legend_position (str): 'below', 'above', 'left', or 'right'
        legend_orientation (str): 'horizontal' or 'vertical'
        widget_position (str): 'below', 'above', 'left', or 'right'
        
        """
        
        self._validate_workflow('render_plot')

        for k in self.columndatasources.keys():
            for suffix in self.remove_columns[k]:
                self.columndatasources[k].data.pop('xs' + suffix)
                self.columndatasources[k].data.pop('ys' + suffix)
        
        if len(self.legend.items) > 0:
            self.legend.orientation = legend_orientation
            self.plot.add_layout(self.legend, legend_position)

        self.plot.toolbar.autohide = self.autohide

        if self.colorbar is not None:
            self.plot = Row(children=[self.plot, self.colorbar])

        if len(self.widgets) > 0:

            if 'animation' in self.widgets.keys():
                animate = True
                button = self.widgets.pop('animation')
                button = button['widget']
            else:
                animate = False
                button = None

            widget_list = [d['widget'] for d in self.widgets.values()]

            if animate:
                if (len(widget_list) > 1) or not isinstance(widget_list[0], bokeh_utils.Slider):
                    raise NotImplementedError(
                        'Animations are currently only implented for plots that have only a Slider widget.'
                    )
                widget_list = [button] + widget_list

            if widget_position not in ('left', 'right', 'above', 'below'):
                raise ValueError("Valid widget positions are 'left', 'right', 'above', 'below'.")
            if widget_position == 'left':
                self.plot = Row(children=[WidgetBox(children=widget_list), self.plot])
            if widget_position == 'right':
                self.plot = Row(children=[self.plot, WidgetBox(children=widget_list)])
            if widget_position == 'above':
                self.plot = Column(children=[WidgetBox(children=widget_list), self.plot])
            if widget_position == 'below':
                self.plot = Column(children=[self.plot, WidgetBox(children=widget_list)])

        if len(self.data_tables) > 0:
            self.plot = Column(children=[self.plot] + self.data_tables)

        self.validation['render_plot'] = True
        
        if display_type == 'notebook':
            output_notebook(CDN, hide_banner=True, load_timeout=60000)
            show(self.plot)
        elif display_type == 'object':
            return self.plot
        else:
            if directory is not None:
                display_type = path.join(directory, display_type)
            save(self.plot, filename='{}.html'.format(display_type), resources=CDN, title=display_type)
            return display_type
