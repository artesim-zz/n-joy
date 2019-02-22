from setuptools import setup

setup(
    name='n-joy',
    version='0.1.0',
    packages=['njoy_core'],
    requires=['pyzmq>=17.1', 'PySDL2>=0.9.6', 'pyvjoy'],
    url='',
    license='Creative Commons Attribution-ShareAlike 4.0 International (https://creativecommons.org/licenses/by-sa/4.0/)',
    author='Artesim',
    author_email='artesim1852@gmail.com',
    description='n-joy is a script engine to program your (potentially remote !) HOTAS, yoke, pedals, etc. It is meant as an open-source alternative to proprietary softwares traditionally coming with them.'
)
