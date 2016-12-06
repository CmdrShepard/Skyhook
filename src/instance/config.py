import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    VERSION = '1.0.0'
    DEBUG = True

    # DATABASE
    SEARCH_CACHE_TIME = 86400
    SHOW_CACHE_TIME = 86400
    DB_HOST = 'localhost'
    DB_USERNAME = 'skyhook'
    DB_PASSWORD = 'skyhook'
    DB_NAME = 'skyhook'
    DB_PORT = 5432

    # TVDB
    # Get TVDB API Key here: http://thetvdb.com/?tab=apiregister
    TVDB_API_KEY = ''
    TVDB_LANGUAGES = ['no', 'da', 'en']

    # SLACK
    SLACK_WEBHOOK = None

    # SQLALCHEMY
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = 'postgresql://' + DB_USERNAME + ':' + DB_PASSWORD + '@' + DB_HOST + ':' + str(DB_PORT) + \
                              '/' + DB_NAME


class DebugConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
