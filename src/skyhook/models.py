from sqlalchemy.dialects.postgresql import JSON
from skyhook import db
from skyhook.logger import Logger
import datetime

logging = Logger(__name__)


class Search(db.Model):
    __tablename__ = 'skyhook_searches'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime(timezone=True))
    search_string = db.Column(db.String)
    language = db.Column(db.String, nullable=True)
    results = db.Column(JSON, nullable=True)

    def __init__(self, date, search_string, language, results):
        self.date = date
        self.search_string = search_string
        self.language = language
        self.results = results


class Show(db.Model):
    __tablename__ = 'skyhook_shows'

    id = db.Column(db.Integer, primary_key=True)
    last_modified = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    tvdb_id = db.Column(db.Integer)
    language = db.Column(db.String, primary_key=True)
    title = db.Column(db.String)
    overview = db.Column(db.String)
    slug = db.Column(db.String)
    first_aired = db.Column(db.DateTime(timezone=True))
    tv_rage_id = db.Column(db.Integer)
    tv_maze_id = db.Column(db.Integer)
    status = db.Column(db.String)
    runtime = db.Column(db.Integer)
    time_of_day = db.Column(db.Integer)
    network = db.Column(db.String)
    imdb_id = db.Column(db.String)
    actors = db.Column(JSON)
    genres = db.Column(JSON)
    content_rating = db.Column(db.String)
    rating_value = db.Column(db.Float)
    rating_count = db.Column(db.Integer)
    images = db.Column(JSON)
    seasons = db.relationship('Season',
                              primaryjoin='Show.title == Season.show_title',
                              foreign_keys='Season.show_title',
                              backref='skyhook_shows',
                              lazy='dynamic'
                              )
    episodes = db.relationship('Episode',
                               primaryjoin='Show.title == Episode.show_title',
                               foreign_keys='Episode.show_title',
                               backref='skyhook_shows',
                               lazy='dynamic'
                               )

    __table_args__ = (
        db.UniqueConstraint('tvdb_id', 'language'),
    )

    def __init__(self, *initial_data, **kwargs):
        for dictionary in initial_data:
            for key in dictionary:
                setattr(self, key, dictionary[key])
        for key in kwargs:
            setattr(self, key, kwargs[key])

    def __repr__(self):
        return '<Show %r>' % self.title

    def to_sonarr_format(self):
        sonarr_format = {
            'tvdbId': self.tvdb_id,
            'language': self.language,
            'title': self.title,
            'overview': self.overview,
            'slug': self.slug,
            'firstAired': self.first_aired.strftime("%Y-%m-%d") if self.first_aired is not None else None,
            'tvRageId': self.tv_rage_id,
            'tvMazeId': self.tv_maze_id,
            'status': self.status,
            'runtime': self.runtime,
            'timeOfDay': {
                'hours': self.time_of_day
            },
            'network': self.network,
            'imdbId': self.imdb_id,
            'actors': self.actors,
            'genres': self.genres,
            'contentRating': self.content_rating,
            'rating': {
                'count': self.rating_count,
                'value': self.rating_value
            },
            'images': self.images,
            'seasons': [],
            'episodes': []
        }

        #sonarr_format['overview'] = '<LANGUAGE: ' + TvDB.get_language(self.language).value + '>\r\n' + (
        #    sonarr_format['overview'] if sonarr_format['overview'] is not None else '')

        if self.images is None:
            sonarr_format.pop('images')

        for season in self.seasons:
            sonarr_format['seasons'].append(season.to_sonarr_format())

        for episode in self.episodes:
            sonarr_format['episodes'].append(episode.to_sonarr_format())

        return sonarr_format

    @staticmethod
    def get_last_absolute_episode_number(show_title):
        episode = (db.session.query(Episode)
                   .filter(Episode.season_number != 0)
                   .filter(Episode.absolute_number is not None)
                   .filter_by(show_title=show_title)
                   .order_by(Episode.absolute_number.desc()).first()
                   )
        #logging.debug(episode)
        if episode is None or episode.absolute_number is None:
            return 0
        else:
            return episode.absolute_number


class Season(db.Model):
    __tablename__ = 'skyhook_seasons'

    id = db.Column(db.Integer, primary_key=True)
    show_title = db.Column(db.String)
    number = db.Column(db.Integer)
    images = db.Column(JSON)
    episodes = db.relationship('Episode', backref='skyhook_seasons')

    __table_args__ = (
        db.UniqueConstraint('show_title', 'number'),
    )

    def __init__(self, show_title, number, images):
        self.show_title = show_title
        self.number = number
        self.images = images

    def __repr__(self):
        return '<Season %r>' % self.number

    def to_sonarr_format(self):
        sonarr_format = {
            'seasonNumber': self.number,
            'images': self.images
        }
        if self.number == 0:
            sonarr_format.pop('seasonNumber')

        if self.images is None:
            sonarr_format.pop('images')
        return sonarr_format

    @staticmethod
    def get_episode_count(number):
        return db.session.query(Episode).filter_by(number=number).count()


class Episode(db.Model):
    __tablename__ = 'skyhook_episodes'

    id = db.Column(db.Integer, primary_key=True)
    show_title = db.Column(db.String)
    tvdb_show_id = db.Column(db.Integer)
    tvdb_id = db.Column(db.Integer)
    season_id = db.Column(db.Integer, db.ForeignKey('skyhook_seasons.id'), nullable=False)
    season_number = db.Column(db.Integer)
    number = db.Column(db.Integer)
    absolute_number = db.Column(db.Integer)
    title = db.Column(db.String)
    air_date = db.Column(db.DateTime(timezone=True))
    air_date_utc = db.Column(db.DateTime(timezone=True))
    rating_value = db.Column(db.Float)
    rating_count = db.Column(db.Integer)
    overview = db.Column(db.String)
    writers = db.Column(JSON)
    directors = db.Column(JSON)
    image = db.Column(db.String)

    __table_args__ = (db.UniqueConstraint('season_id', 'number'),)

    def __init__(self, show_title, tvdb_show_id, tvdb_id, season_id, number,
                 absolute_number, title, air_date, air_date_utc, rating_value,
                 rating_count, overview, writers, directors, image
                 ):
        self.show_title = show_title
        self.tvdb_show_id = tvdb_show_id
        self.tvdb_id = tvdb_id
        self.season_id = season_id
        self.number = number
        self.absolute_number = absolute_number
        self.title = title
        self.air_date = air_date
        self.air_date_utc = air_date_utc
        self.rating_value = rating_value
        self.rating_count = rating_count
        self.overview = overview
        self.writers = writers
        self.directors = directors
        self.image = image

        # Dirty trick to set the absolute episode number
        # FIXME
        season = self.get_season()
        self.season_number = season.number
        #logging.debug('Season number: ' + str(season.number))
        if self.absolute_number is None:
            if int(season.number) > 0:
                self.absolute_number = Show.get_last_absolute_episode_number(show_title=show_title)
                self.absolute_number += 1

        if int(season.number) > 0 and self.absolute_number is None:
            logging.error('Absolute number is None for show "' + self.show_title + '": season ' + str(self.get_season().number) + ' episode ' + str(self.number))

    def __repr__(self):
        return '<Episode %r>' % self.title

    def get_season(self):
        return Season.query.get(self.season_id)

    def to_sonarr_format(self):
        season = self.get_season()
        sonarr_format = {
            'tvdbShowId': self.tvdb_show_id,
            'tvdbId': self.tvdb_id,
            'seasonNumber': season.number,
            'episodeNumber': self.number,
            'absoluteEpisodeNumber': self.absolute_number,
            'title': self.title,
            'airDate': self.air_date.strftime('%Y-%m-%d') if self.air_date is not None else None,
            'airDateUtc': self.air_date_utc.strftime('%Y-%m-%dT%H:%M:%SZ') if self.air_date_utc is not None else None,
            'rating': {
                'count': self.rating_count,
                'value': self.rating_value
            },
            'overview': self.overview,
            'writers': self.writers,
            'directors': self.directors,
            'image': self.image
        }
        if int(season.number) == 0:
            sonarr_format.pop('seasonNumber')

        if self.writers is None:
            sonarr_format.pop('writers')

        if self.directors is None:
            sonarr_format.pop('directors')

        if self.image is None:
            sonarr_format.pop('image')
        return sonarr_format
