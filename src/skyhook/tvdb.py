import datetime
from enum import Enum
import pytz
import dateutil.parser
import requests
import tvdb_api
import pytvmaze
from lxml import html
from skyhook.logger import Logger
from skyhook.models import Show

logging = Logger(__name__)


class Language(Enum):
    en = 'English'
    sv = 'Svenska'
    no = 'Norsk'
    da = 'Dansk'
    fi = 'Suomeksi'
    nl = 'Nederlands'
    de = 'Deutsch'
    it = 'Italiano'
    es = 'Español'
    fr = 'Français'
    pl = 'Polski'
    hu = 'Magyar'
    el = 'Greek'
    tr = 'Turkish'
    ru = 'Russian'
    he = 'Hebrew'
    ja = 'Japanese'
    pt = 'Portuguese'
    zh = 'Chinese'
    cs = 'Czech'
    sl = 'Slovenian'
    hr = 'Croatian'
    ko = 'Korean'


class LanguageTimezone(Enum):
    en = 'EST'
    sv = 'Europe/Stockholm'
    no = 'Europe/Oslo'
    da = 'Europe/Copenhagen'
    fi = 'Europe/Helsinki'
    nl = 'Europe/Amsterdam'
    de = 'Europe/Berlin'
    it = 'Europe/Rome'
    es = 'Europe/Madrid'
    fr = 'Europe/Paris'
    pl = 'Europe/Warsaw'
    hu = 'Europe/Budapest'
    el = 'Europe/Athens'
    tr = 'Europe/Istanbul'
    ru = 'Europe/Moscow'
    he = 'Asia/Jerusalem'
    ja = 'Asia/Tokyo'
    pt = 'Europe/Lisbon'
    zh = 'Asia/Shanghai'
    cs = 'Europe/Prague'
    sl = 'Europe/Bratislava'
    hr = 'Europe/Zagreb'
    ko = 'Asia/Seoul'


class TvDB:
    def __init__(self, api_key):
        self.tvdb = tvdb_api.Tvdb(
            apikey=api_key,
            actors=True,
            banners=True,
            search_all_languages=False,
            select_first=False,
            cache=True,
            language=None,
            useZip=False
        )

    def get_tvdb(self, api_key, language):
        return tvdb_api.Tvdb(
            apikey=api_key,
            actors=True,
            banners=True,
            search_all_languages=False,
            select_first=False,
            cache=True,
            language=language,
            useZip=False
        )

    @staticmethod
    def get_language(abbreviation):
        return Language[abbreviation]

    def get_show(self, tvdb_id):
        return self.tvdb.search(tvdb_id)

    def search(self, string, language, tvdb_id=None):
        # TODO: Language
        from skyhook import app
        search_results = None
        if tvdb_id is not None:
            # Get the show name by parsing the HTML DOM.
            # The TVDB API does not provide a method to grab the show by ID.
            # http://thetvdb.com/?tab=series&id=299964&lid=9
            for language in app.config['TVDB_LANGUAGES']:
                lid = self.tvdb.config['langabbv_to_id'][language]
                r = requests.get('http://thetvdb.com/?tab=series&id=' + str(tvdb_id) + '&lid=' + str(lid))
                if r.status_code != 200:
                    continue
                tree = html.fromstring(r.content)
                title = tree.findtext('.//title')
                title = title.replace(': Series Info', '')
                if title == '':
                    # Show not found, continue
                    continue
                string = title
                break
            if string is None:
                # Fallback to TV MAZE
                try:
                    # Try to grab the series name from Maze TV via TVDB ID.
                    tvmaze = self.get_tvmaze(tvdb_id)
                    string = tvmaze.name
                except pytvmaze.ShowNotFound:
                    logging.debug('TVMaze Show not found with TVDB ID: ' + tvdb_id)
                    return None
        for language in app.config['TVDB_LANGUAGES']:
            logging.debug('Searching TVDB for ' +
                          ('ID=' + tvdb_id if tvdb_id is not None else 'NAME="' + string + '"') +
                          ' and language "' + language + '"')
            # Override from the TVDB API
            self.tvdb.config['language'] = language
            self.tvdb.config[
                'url_getSeries'] = u"%(base_url)s/api/GetSeries.php?seriesname=%%s&language=%(language)s" % self.tvdb.config
            results = self.tvdb.search(string)
            if results is not None:
                # Loop through the results and only match the exact search string / tvdb id
                for result in results:
                    if language != result['language']:
                        continue
                    if tvdb_id is not None and str(tvdb_id) == str(result['id']):
                        # Only return 1 result if we are searching with tv db id's
                        return [result]
                    elif result['seriesname'].lower() == string.lower():
                        if search_results is None:
                            search_results = []
                        # Append the show to the search results
                        search_results.append(result)
        return search_results

    def get_tvmaze(self, tvdb_id):
        return pytvmaze.get_show(tvdb_id=tvdb_id)

    def to_sonarr_format(self, result):
        show = self.tvdb[result['id']]
        original_show = show
        tvmaze_id = None
        tvrage_id = None
        try:
            tvmaze = self.get_tvmaze(result['id'])
            tvmaze_id = tvmaze.id
            if 'tvrage' in tvmaze.externals:
                tvrage_id = tvmaze.externals['tvrage']
        except pytvmaze.ShowNotFound:
            logging.info('TVMaze Show not found: ' + str(result['id']))
            pass
        except pytvmaze.IDNotFound:
            logging.info('TVMaze ID not found: ' + str(result['id']))
            pass
        if show['seriesname'] is None:
            if show.data is None:
                raise Exception('Missing series')
            show = show.data
        sonarr_format = {
            'tvdbId': result['id'],
            'title': result['seriesname'],
            'overview': result['overview'] if 'overview' in result else None,
            'slug': result['seriesname'].lower().replace(' ', '-'),
            'language': result['language'] if 'language' in result else None,
            'lid': result['lid'] if 'lid' in result else None,
            'firstAired': result['firstaired'] if 'firstaired' in result else None,
            'tvRageId': tvrage_id,
            'tvMazeId': tvmaze_id,
            'status': show['status'],
            'runtime': show['runtime'],
            'timeOfDay': {
                'hours': dateutil.parser.parse(show['airs_time']).hour if show['airs_time'] is not None else None,
                'minutes': dateutil.parser.parse(show['airs_time']).minute if show['airs_time'] is not None else None
            },
            'network': result['network'] if 'network' in result else None,
            'imdbId': show['imdb_id'],
            'genres': show['genre'].split('|')[1:-1] if show['genre'] is not None else None,
            'actors': None,
            'contentRating': show['contentrating'],
            'rating': {
                'count': show['ratingcount'],
                'value': show['rating']
            }
        }

        # Images
        for cover_type in ['fanart', 'banner', 'poster']:
            if 'images' not in sonarr_format:
                sonarr_format['images'] = []
            if show[cover_type]:
                sonarr_format['images'].append({
                    'coverType': cover_type.capitalize(),
                    'url': show[cover_type]
                })

        # Episodes
        episode_seasons = []
        sonarr_episodes = []
        for season in original_show.values():
            for episode in season.values():
                if episode['seasonnumber'] not in episode_seasons:
                    episode_seasons.append(int(episode['seasonnumber']))
                sonarr_episode = {
                    'tvdbShowId': result['id'],
                    'tvdbId': episode['id'],
                    'episodeNumber': int(episode['episodenumber']),
                    'title': episode['episodename'],
                    'airDate': episode['firstaired'],
                    'airDateUtc': None,
                    'rating': {
                        'count': episode['ratingcount'],
                        'value': episode['rating']
                    },
                    'overview': episode['overview'],
                    'image': episode['filename']
                }

                if episode['firstaired'] is not None and sonarr_format['timeOfDay']['hours'] is not None:
                    if episode['language'] in LanguageTimezone.__members__:
                        episode_timezone = LanguageTimezone[episode['language']].value
                    else:
                        episode_timezone = 'EST'
                    timezone = pytz.timezone(episode_timezone)
                    date = (dateutil.parser.parse(episode['firstaired']) +
                            datetime.timedelta(
                                hours=sonarr_format['timeOfDay']['hours'],
                                minutes=sonarr_format['timeOfDay']['minutes']
                            ))
                    date = timezone.localize(date)
                    date = date.astimezone(pytz.timezone('UTC'))
                    sonarr_episode['airDateUtc'] = date.strftime("%Y-%m-%dT%H:%M:%SZ")

                if int(episode['seasonnumber']) > 0:
                    sonarr_episode['seasonNumber'] = int(episode['seasonnumber'])

                #if episode['absolute_number'] is None:
                #    if int(episode['seasonnumber']) > 0:
                #        sonarr_episode['absoluteEpisodeNumber'] = Show.get_last_absolute_episode_number(show_title=sonarr_format['title'])
                #        sonarr_episode['absoluteEpisodeNumber'] += 1

                if episode['absolute_number'] is not None:
                    sonarr_episode['absoluteEpisodeNumber'] = episode['absolute_number']

                if 'director' in episode and episode['director'] is not None:
                    if '|' in episode['director']:
                        sonarr_episode['directors'] = episode['director'].split('|')[1:-1]
                    else:
                        sonarr_episode['directors'] = [episode['director']]

                if 'writer' in episode and episode['writer'] is not None:
                    if '|' in episode['writer']:
                        sonarr_episode['writers'] = episode['writer'].split('|')[1:-1]
                    else:
                        sonarr_episode['writers'] = [episode['writer']]

                sonarr_episodes.append(sonarr_episode)
        sonarr_format['episodes'] = sonarr_episodes

        # Seasons
        banners = self.tvdb[result['id']]['_banners']
        if banners and 'season' in banners:
            sonarr_banners = []
            inner_banners = {}

            for banner_key in ['season', 'seasonwide']:
                if banner_key not in banners['season']:
                    continue
                best_posters = {}
                best_ratings = {}
                poster_seasons = []
                for poster_id in banners['season'][banner_key]:
                    poster = banners['season'][banner_key][poster_id]
                    poster['season'] = int(poster['season'])
                    poster_seasons.append(poster['season'])
                    if 'rating' in poster:
                        # Select the best rated poster
                        if poster['season'] not in best_ratings:
                            best_posters[poster['season']] = poster
                            best_ratings[poster['season']] = float(poster['rating'])
                        elif (int(poster['ratingcount']) > 1 and
                                      float(poster['rating']) > best_ratings[poster['season']]):
                            best_posters[poster['season']] = poster
                            best_ratings[poster['season']] = float(poster['rating'])
                # Let's make sure we have posters for every season
                for season in poster_seasons:
                    if season not in best_posters:
                        # We're missing a season, let's ignore the ratings and just grab the first one
                        for poster_id in banners['season'][banner_key]:
                            poster = banners['season'][banner_key][poster_id]
                            poster['season'] = int(poster['season'])
                            if poster['season'] is season:
                                # Found a poster for a missing season, add it to the list
                                best_posters[poster['season']] = poster
                                break

                # Add the best poster to the season
                for season in best_posters:
                    poster = best_posters[season]
                    if banner_key == 'season':
                        cover_type = 'Poster'
                    else:
                        cover_type = 'Banner'

                    if season not in inner_banners:
                        inner_banners[season] = {}
                    inner_banners[season][cover_type] = poster['_bannerpath']

            for season in inner_banners:
                sonarr_banner = {}
                season_banners = inner_banners[season]
                if season > 0:
                    sonarr_banner['seasonNumber'] = int(season)
                for banner_key in season_banners:
                    if 'images' not in sonarr_banner:
                        sonarr_banner['images'] = []
                    if banner_key in season_banners:
                        sonarr_banner['images'].append({
                            'coverType': banner_key,
                            'url': season_banners[banner_key]
                        })
                sonarr_banners.append(sonarr_banner)
            sonarr_format['seasons'] = sonarr_banners

        # Seasons fallback
        if 'seasons' not in sonarr_format:
            sonarr_seasons = []
            for season in original_show.values():
                for org_episode in season.values():
                    episode = org_episode
                    break;
                # FIXME: episode = season[1]
                sonarr_seasons.append({
                    'seasonNumber': int(episode['seasonnumber'])
                })
            sonarr_format['seasons'] = sonarr_seasons
        # Seasons fallback end

        # Add seasons that are missing banners/posters
        if len(episode_seasons) > len(sonarr_format['seasons']):
            current_seasons = []
            for season in sonarr_format['seasons']:
                if 'seasonnumber' in season:
                    current_seasons.append(int(season['seasonnumber']))

            for season in episode_seasons:
                if season not in current_seasons:
                    sonarr_format['seasons'].append({
                        'seasonNumber': int(season),
                        'images': None
                    })
        # Add seasons that are missing banners/posters end

        if not sonarr_format['seasons']:
            logging.error('Season list for show ' + sonarr_format['title'] + ' is empty')
            raise Exception('Season list for show ' + sonarr_format['title'] + ' is empty')
        # Seasons end

        # Actors
        actors = self.tvdb[result['id']]['_actors']
        if actors:
            sonarr_actors = []
            for actor in actors:
                sonarr_actor = {}
                if actor['name'] is not None:
                    sonarr_actor['name'] = actor['name']
                if actor['role'] is not None:
                    sonarr_actor['character'] = actor['role']
                sonarr_actors.append(sonarr_actor)
            sonarr_format['actors'] = sonarr_actors
        # Actors end

        return sonarr_format
