import flask
import json

from flask import request, Response
from skyhook import app, tvdb

from skyhook.cache import SonarrCache, handle_search
from skyhook.logger import Logger
from skyhook.models import Show

logging = Logger(__name__)

def handle_results(search_string, language):
    sonarr_results = []
    if SonarrCache.has_cached_results(search_string, language):
        logging.info('Found cached results for search string "' + search_string + '"')
        cached_result = SonarrCache.get_cached_results(search_string, language)
        for tvdb_ids in cached_result.results:
            if language is None:
                cached_show = SonarrCache.get_cached_show(tvdb_ids, cached_result.language).to_sonarr_format()
                cached_show.pop('episodes', None)
                sonarr_results.append(cached_show)
            else:
                cached_show = SonarrCache.get_cached_show(tvdb_ids, language).to_sonarr_format()
                cached_show.pop('episodes', None)
                sonarr_results.append(cached_show)
    else:
        results = tvdb.search(search_string, language)
        sonarr_results = handle_search(search_string, results, with_episodes=False)
    # FIXME: dirty workaround to make sure we send the proper results
    if isinstance(sonarr_results, Show):
        sonarr_results = [sonarr_results.to_sonarr_format()]
    else:
        for i in range(0, len(sonarr_results)):
            if isinstance(sonarr_results[i], Show):
                sonarr_results[i] = sonarr_results[i].to_sonarr_format()
    return sonarr_results


@app.route('/v1/tvdb/search/<language>/')
def search(language):
    # TODO: Language
    language = None

    search_string = str(request.args.get('term'))
    logging.info(search_string)

    # Language search
    if 'lang:' in search_string:
        search_split = search_string.split()
        for search_item in search_split:
            if search_item.startswith('lang:'):
                language = search_item[5:]
                search_string = search_string.replace(search_item, '').strip()
                break

    logging.debug('Searching for ' + search_string)
    if search_string is None:
        flask.abort(400)

    sonarr_results = handle_results(search_string, language)

    return Response(json.dumps(sonarr_results), mimetype='application/json')


@app.route('/v1/tvdb/shows/<language>/<tvdb_id>')
def shows(language, tvdb_id):
    # TODO: Language
    language = None
    cached_show = SonarrCache.get_cached_show(tvdb_id, language, True)
    if isinstance(cached_show, Show):
        cached_show = cached_show.to_sonarr_format()
    return Response(json.dumps(cached_show), mimetype='application/json')


