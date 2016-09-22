from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from instance.config import DebugConfig

app = Flask(__name__)
app.config.from_object(DebugConfig)
db = SQLAlchemy(app)

from skyhook.tvdb import TvDB
tvdb = TvDB(app.config['TVDB_API_KEY'])

print('Starting Sonarr Skyhook v' + app.config['VERSION'])
import skyhook.models
db.create_all()
import skyhook.views
