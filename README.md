# Theto: workflow automation for exploring location data

Any visualization requires a large number of trivial decisions that, when added up, result in a non-trivial 
impact on the quality and usability of the visualization. This is especially true of geospatial visualization,
where data needs to transformed fit a particular map projection or a particular map tile service needs to be 
configured to contextualize the plot. `Theto` abstracts a lot of this overhead so more time can be devoted
to looking at and understanding the data. A `Theto` instance allows users to:

1. Store api keys, palettes, and other static resources repeatedly needed throughout a typical visualization 
pipeline.
2. Load data sources, format coordinate data to stage it for all foreseeable downstream needs, and append metadata. 
3. Add widgets to interactively filter what the final visualization shows, and infer the appropriate parameters
for those widgets based on the source data.
4. Determine plot bounds, size, map zoom level, and other parameters in ways that accommodate the data. 
5. Add layers of visualization, including tooltips and other visual aids, including connections between data points.
6. Render the plot, either in the notebook or by saving to file, optionally appending an interactive legend.

"Theto" is a transliteration of the Greek word Θέτω, which means "I place" or "I situate", or simply "I put". 
That's what the tool does: it puts geospatial data where it needs to be so users can spend their time looking
at and making sense of what's there.

A Jupyter notebook demonstrating a lot of `Theto`'s functionality can be found here:

https://nbviewer.jupyter.org/github/Valassis-Digital-Media/theto/blob/master/theto_demo_notebook.ipynb

## Installation
To install from PyPI:

`pip install theto`

`conda` installation coming soon.

## Supported data representations
Data can be loaded in a variety of formats (geohashes, WKT, shapely objects, GeoJSON, or coordinate pairs). The tool 
will automatically detect the format and process it appropriately. Likewise, any input can be rendered as the original 
shape itself (a polygon) or as the centroid of the shape (a point). Polygons are rendered using Bokeh's 
`MultiPolygons` glyph. Points can be rendered using any of Bokeh's marker glyphs.

## Limitations
`Theto` is designed for interactive exploration, and is therefore appropriate for small-to-medium sized data. 
A very rough benchmark indicated that it takes about 5 seconds to plot every 50,000 points (a polygon might contain 
very many individual points) in a Jupyer notebook, and the notebook freezes at around 250,000 points. Outputting to 
file and viewing in a separate browser window should allow up to around 1 million points. For larger visualization, 
see http://datashader.org/.

## Contributing
We welcome issues and pull requests that help improve the variety of data sources and plot elements Theto 
supports, its usability, and its re-usability within other tools.

## License
Copyright (c) 2019 Valassis Digital under the terms of the BSD 3-Clause license