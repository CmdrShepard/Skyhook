# Always prefer setuptools over distutils
from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='skyhook',
    version='1.0.0',
    description='Wrapper for the Sonarr Skyhook (TVDB API Wrapper)',
    long_description=long_description,
    url='https://github.com/CmdrShepard/Skyhook',
    author='Commander Shepard',
    author_email='CommanderShepardTorrents@gmail.com',
    license='GPLv3',
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3.5',
    ],
    keywords='skyhook sonarr tracker torrents tvdb tvmaze',
    packages=find_packages(),
    install_requires=[
        'Flask==0.10.1',
        'Flask-SQLAlchemy==2.1',
        'lxml==3.6.0',
        'psycopg2==2.6.1',
        'python-dateutil==2.5.3',
        'pytvmaze==1.5.1',
        'pytz==2016.4',
        'requests==2.10.0',
        'slackweb==1.0.5',
        'tvdb-api==1.10'
    ],
    extras_require={
        'dev': ['tox', 'isort', 'flake8']
    }
)
