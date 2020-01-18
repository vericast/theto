from setuptools import setup, find_packages

try:
    with open('README.md') as f:
        long_description = f.read()
except:
    long_description = ''
    print('Failed to load README.md as long_description')

setup(
    name='theto',
    version='0.2.1',
    description='Workflow automation for exploring location data',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Valassis Digital',
    url='https://github.com/Valassis-Digital-Media/theto',
    platforms=['Linux', 'Mac OSX', 'Windows'],
    packages=find_packages(),
    include_package_data=True,
    license='BSD 3-Clause',
    install_requires=[
        'bokeh>=1.0',
        'pandas',
        'numpy',
        'shapely',
        'pyproj'
    ],
)