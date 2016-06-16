import datetime
import pytz
from skyhook import app, tvdb, db
from skyhook.exceptions import CacheShowLanguage
from skyhook.logger import Logger
from sqlalchemy.orm.exc import NoResultFound

from skyhook.models import Show, Search, Season, Episode

logging = Logger(__name__)


def handle_search(search_string, results, with_episodes=True):
    sonarr_results = []
    search_results = {}
    if results is None:
        SonarrCache.update_search(search_string, 'en', search_results)
        return sonarr_results
    for result in results:
        sonarr_format = tvdb.to_sonarr_format(result)
        if result['language'] not in search_results:
            search_results[result['language']] = []
        search_results[result['language']].append(result['id'])
        SonarrCache.update_show(result['id'], sonarr_format)
        #if with_episodes is False:
        #    sonarr_format.pop('episodes', None)
        language = sonarr_format['language']
        show = SonarrCache.get_cached_show(tvdb_id=result['id'], language=result['language'])
        sonarr_results.append(show)
	#sonarr_results.append(sonarr_format)
    for language in search_results:
        SonarrCache.update_search(search_string, language, search_results[language])
    return sonarr_results


class SonarrCache:
    cache_time = 86400

    @classmethod
    def has_season(cls, show_title, season):
        try:
            db.session.query(Season).filter_by(show_title=show_title, number=season).one()
            return True
        except NoResultFound:
            return False

    @classmethod
    def has_episode(cls, season_id, episode):
        try:
            db.session.query(Episode).filter_by(season_id=season_id, number=episode).one()
            return True
        except NoResultFound:
            return False

    @classmethod
    def update_search(cls, search_string, language, results):
        search_string = search_string.lower()
        if cls.has_cached_results(search_string=search_string, language=language):
            logging.debug('Updating Sonarr search cache for search string "' + search_string + '" and language "' +
                          language + '": ' + str(len(results)) + ' Results')
            instance = cls.get_cached_results(search_string=search_string, language=language)
            instance.date = datetime.datetime.now()
            instance.results = results
            db.session.commit()
        else:
            logging.debug('Adding new Sonarr search cache for search string "' + search_string + '" and language "' +
                          language + '": ' + str(len(results)) + ' Results')
            new_search = Search(
                search_string=search_string,
                language=language,
                date=datetime.datetime.now(),
                results=results
            )
            db.session.add(new_search)
            db.session.commit()

    @classmethod
    def update_show(cls, tvdb_id, sonarr_format):
        language = sonarr_format['language']
        try:
            show = cls.get_cached_show(tvdb_id=tvdb_id, language=language)
            show.title = sonarr_format['title']
            show.slug = sonarr_format['slug']
            show.overview = sonarr_format['overview']
            show.first_aired = sonarr_format['firstAired']
            show.tv_rage_id = sonarr_format['tvRageId']
            show.tv_maze_id = sonarr_format['tvMazeId']
            show.status = sonarr_format['status']
            show.time_of_day = sonarr_format['timeOfDay']['hours']
            show.network = sonarr_format['network']
            show.imdb_id = sonarr_format['imdbId']
            show.actors = sonarr_format['actors']
            show.genres = sonarr_format['genres']
            show.content_rating = sonarr_format['contentRating']
            show.rating_value = sonarr_format['rating']['value']
            show.rating_count = sonarr_format['rating']['count']
            show.images = sonarr_format['images']
            db.session.commit()
            logging.debug('Updated Sonarr show in cache: "' + show.title + '"')

            for season in sonarr_format['seasons']:
                number = season['seasonNumber'] if 'seasonNumber' in season else 0
                if cls.has_season(show.title, number):
                    cached_show = db.session.query(Season).filter_by(show_title=show.title, number=number).one()
                    cached_show.images = season['images'] if 'images' in season else None
                    db.session.commit()
                    logging.debug('Updated Sonarr season to cache: "' + show.title + '" Season ' +
                                  str(cached_show.number))
                else:
                    new_season = Season(
                        show_title=show.title,
                        number=number,
                        images=season['images'] if 'images' in season else None
                    )
                    db.session.add(new_season)
                    db.session.commit()
                    logging.debug('Added new Sonarr season to cache: "' + show.title + '" Season ' +
                                  str(new_season.number))

            for episode in sonarr_format['episodes']:
                season = episode['seasonNumber'] if 'seasonNumber' in episode else 0
                number = episode['episodeNumber'] if 'episodeNumber' in episode else None
                season = db.session.query(Season).filter_by(show_title=show.title, number=season).one()
                if cls.has_episode(season.id, number):
                    absolute_number = episode['absoluteEpisodeNumber'] if 'absoluteEpisodeNumber' in episode else None
                    cached_episode = db.session.query(Episode).filter_by(season_id=season.id, number=number).one()
                    cached_episode.tvdb_id = episode['tvdbId'] if 'tvdbId' in episode else None,
                    cached_episode.absolute_number = absolute_number,
                    cached_episode.title = episode['title'] if 'title' in episode else None,
                    cached_episode.air_date = episode['airDate'] if 'airDate' in episode else None,
                    cached_episode.air_date_utc = episode['airDateUtc'] if 'airDateUtc' in episode else None,
                    cached_episode.rating_count = episode['rating']['count'] if 'rating' in episode else None,
                    cached_episode.rating_value = episode['rating']['value'] if 'rating' in episode else None,
                    cached_episode.overview = episode['overview'] if 'overview' in episode else None,
                    cached_episode.writers = episode['writers'] if 'writers' in episode else None,
                    cached_episode.directors = episode['directors'] if 'directors' in episode else None,
                    cached_episode.image = episode['image'] if 'image' in episode else None
                    db.session.commit()
                    logging.debug('Updated Sonarr episode to cache: "' + show.title + '" Season ' +
                                  str(season.number) + ' Episode ' + str(cached_episode.number) + ' [Absolute number: ' + str(cached_episode.absolute_number) + ']')
                else:
                    absolute_number = episode['absoluteEpisodeNumber'] if 'absoluteEpisodeNumber' in episode else None
                    new_episode = Episode(
                        show_title=show.title,
                        season_id=season.id,
                        tvdb_show_id=episode['tvdbShowId'] if 'tvdbShowId' in episode else None,
                        tvdb_id=episode['tvdbId'] if 'tvdbId' in episode else None,
                        number=number,
                        absolute_number=absolute_number,
                        title=episode['title'] if 'title' in episode else None,
                        air_date=episode['airDate'] if 'airDate' in episode else None,
                        air_date_utc=episode['airDateUtc'] if 'airDateUtc' in episode else None,
                        rating_count=episode['rating']['count'] if 'rating' in episode else None,
                        rating_value=episode['rating']['value'] if 'rating' in episode else None,
                        overview=episode['overview'] if 'overview' in episode else None,
                        writers=episode['writers'] if 'writers' in episode else None,
                        directors=episode['directors'] if 'directors' in episode else None,
                        image=episode['image'] if 'image' in episode else None
                    )
                    db.session.add(new_episode)
                    db.session.commit()
                    logging.debug('Added new Sonarr episode to cache: "' + show.title + '" Season ' +
                                  str(season.number) + ' Episode ' + str(new_episode.number) + ' [Absolute number: ' + str(new_episode.absolute_number) + ']')
        except NoResultFound:
            new_show = Show(
                tvdb_id=tvdb_id,
                language=language,
                title=sonarr_format['title'],
                overview=sonarr_format['overview'],
                slug=sonarr_format['slug'],
                first_aired=sonarr_format['firstAired'],
                tv_rage_id=sonarr_format['tvRageId'],
                tv_maze_id=sonarr_format['tvMazeId'],
                status=sonarr_format['status'],
                runtime=sonarr_format['runtime'],
                time_of_day=sonarr_format['timeOfDay']['hours'],
                network=sonarr_format['network'],
                imdb_id=sonarr_format['imdbId'],
                actors=sonarr_format['actors'],
                genres=sonarr_format['genres'],
                content_rating=sonarr_format['contentRating'],
                rating_value=sonarr_format['rating']['value'],
                rating_count=sonarr_format['rating']['count'],
                images=sonarr_format['images']
            )
            db.session.add(new_show)
            db.session.commit()
            logging.debug('Added new Sonarr show to cache: "' + new_show.title + '"')

            for season in sonarr_format['seasons']:
                number = season['seasonNumber'] if 'seasonNumber' in season else 0
                if cls.has_season(new_show.title, number):
                    continue
                new_season = Season(
                    show_title=new_show.title,
                    number=number,
                    images=season['images'] if 'images' in season else None
                )
                db.session.add(new_season)
                db.session.commit()
                logging.debug('Added new Sonarr season to cache: "' + new_show.title + '" Season ' +
                              str(new_season.number))

            for episode in sonarr_format['episodes']:
                season = episode['seasonNumber'] if 'seasonNumber' in episode else 0
                number = episode['episodeNumber'] if 'episodeNumber' in episode else None
                season = db.session.query(Season).filter_by(show_title=new_show.title, number=season).one()
                if cls.has_episode(season.id, number):
                    continue
                new_episode = Episode(
                    show_title=new_show.title,
                    season_id=season.id,
                    tvdb_show_id=episode['tvdbShowId'] if 'tvdbShowId' in episode else None,
                    tvdb_id=episode['tvdbId'] if 'tvdbId' in episode else None,
                    number=number,
                    absolute_number=episode['absoluteEpisodeNumber'] if 'absoluteEpisodeNumber' in episode else None,
                    title=episode['title'] if 'title' in episode else None,
                    air_date=episode['airDate'] if 'airDate' in episode else None,
                    air_date_utc=episode['airDateUtc'] if 'airDateUtc' in episode else None,
                    rating_count=episode['rating']['count'] if 'rating' in episode else None,
                    rating_value=episode['rating']['value'] if 'rating' in episode else None,
                    overview=episode['overview'] if 'overview' in episode else None,
                    writers=episode['writers'] if 'writers' in episode else None,
                    directors=episode['directors'] if 'directors' in episode else None,
                    image=episode['image'] if 'image' in episode else None
                )
                db.session.add(new_episode)
                db.session.commit()
                logging.debug('Added new Sonarr episode to cache: "' + new_show.title + '" Season ' +
                              str(season.number) + ' Episode ' + str(new_episode.number) + ' [Absolute number: ' + str(new_episode.absolute_number) + ']')

    @classmethod
    def map_languages(cls, shows):
        mapped_shows = {}
        for show in shows:
            mapped_shows[show.language] = show
        return mapped_shows

    @classmethod
    def get_cached_show(cls, tvdb_id, language):
        try:
            result = None
            if language is None:
                cached_results = cls.map_languages(db.session.query(Show).filter_by(tvdb_id=tvdb_id))
                for language in app.config['TVDB_LANGUAGES']:
                    if language in cached_results:
                        result = cached_results[language]
                        break
            else:
                result = db.session.query(Show).filter_by(tvdb_id=tvdb_id, language=language)
                if result is not None:
                     result = result.one()

            # Update cached show by grabbing the show from tv maze by tvdb id.
            if result is None:
                logging.debug('Trying to grab show from TV maze with TVDB ID: ' + str(tvdb_id))
                search_results = tvdb.search(None, None, tvdb_id=tvdb_id)
                if search_results is not None:
                    search_result = handle_search(tvdb_id, search_results)[0]
                    return search_result
            if result is None:
                logging.error('Cached Sonarr show not found for TVDB ID "' + str(tvdb_id))
                raise CacheShowLanguage
            logging.debug('Found cached Sonarr show for TVDB ID "' + str(tvdb_id) + '" and language "' + language + '"')
            return result
        except NoResultFound:
            raise NoResultFound('No cached Sonarr show found for TVDB ID "' + str(tvdb_id) + '" and language "' +
                                language + '"')

    @classmethod
    def has_cached_results(cls, search_string, language=None):
        search_string = search_string.lower()
        try:
            if language is None:
                result = None
                cached_results = cls.map_languages(db.session.query(Search).filter_by(search_string=search_string))
                for language in app.config['TVDB_LANGUAGES']:
                    if language in cached_results:
                        result = cached_results[language]
                        break
            else:
                result = db.session.query(Search).filter_by(search_string=search_string, language=language).one()

            if result is None:
                logging.debug('Did not find any Sonarr cached search results for "' + str(search_string) +
                              '" and language "' + (language if language is not None else 'None') + '"')
            elif result.date + datetime.timedelta(0, app.config['SEARCH_CACHE_TIME']) < datetime.datetime.now(pytz.utc):
                logging.debug('Found cached Sonarr search result for "' + str(search_string) + '" and language "' +
                              (language if language is not None else 'None') + '", but cache time was past')
                return False
            else:
                logging.debug('Found cached Sonarr search result for "' + str(search_string) + '" and language "' +
                              (language if language is not None else 'None') + '"')
                return True
        except NoResultFound:
            logging.debug('No cached Sonarr search result found for "' + str(search_string) + '" and language "' +
                          (language if language is not None else 'None') + '"')
            return False

    @classmethod
    def get_cached_results(cls, search_string, language=None):
        search_string = search_string.lower()
        try:
            if language is None:
                result = None
                cached_results = cls.map_languages(db.session.query(Search).filter_by(search_string=search_string))
                for language in app.config['TVDB_LANGUAGES']:
                    if language in cached_results:
                        result = cached_results[language]
                        break
            else:
                result = db.session.query(Search).filter_by(search_string=search_string, language=language).one()
            logging.debug('Returning cached Sonarr search results for "' + str(search_string) + ' and language "' +
                          (language if language is not None else 'None') + '"')
            return result
        except NoResultFound:
            logging.error('Failed to get cached Sonarr search results for "' + str(search_string) + '"')
            raise NoResultFound
