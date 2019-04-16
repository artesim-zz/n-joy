from setuptools import setup

setup(
    name='n-joy',
    version='0.4.0',
    packages=['njoy_core'],
    requires=['pyzmq>=18', 'PySDL2>=0.9.6', 'pyvjoy', 'lark-parser>=0.6.7'],
    tests_requires=['pytest>=4.3.1', 'pytest-mock>=1.10'],
    url='http://www.n-joy.io/',
    license='Creative Commons Attribution-ShareAlike 4.0 International (https://creativecommons.org/licenses/by-sa/4.0/)',
    author='Artesim',
    author_email='artesim1852@gmail.com',
    description='n-joy is a script engine to program your (potentially remote !) HOTAS, yoke, pedals, etc. It is meant as an open-source alternative to proprietary softwares traditionally coming with them.'
)
