#!/usr/bin/env python
import shelve
import os
import sys
from itertools import chain
from doze import url
import json
import logging
import requests
import requests_cache
import json
from wsgiref.simple_server import make_server
from webob.dec import wsgify
from webob import Response
import webbrowser

requests_cache.install_cache()

USERNAME=os.environ['USERNAME']
PLAYLIST=os.environ['PLAYLIST']
CLIENT_ID=os.environ['CLIENT_ID']
CLIENT_SECRET=os.environ['CLIENT_SECRET']
REDIRECT_URI='http://local.ericmoritz.name:8000/'

STATE=shelve.open('.state')

logging.basicConfig(level=logging.INFO)

accounts_service = url('https://accounts.spotify.com')
spotify_service = url('https://api.spotify.com/v1')
playlist_resource = spotify_service.users(USERNAME).playlists(PLAYLIST).tracks

def lines(filenames):
    return chain.from_iterable(
        open(fn)
        for fn in filenames
    )

def _spotify_get(url, *args, **kwargs):
    logging.info("Getting {}".format(url))
    kwargs['headers'] = dict(auth_headers(), **kwargs.get('headers', {}))
    return json.loads(
        requests.get(
            str(url),
            *args, **kwargs
        ).content
    )


def _spotify_put(url, *args, **kwargs):
    logging.info("PUT {} with {!r}".format(url, kwargs.get('data')))
    kwargs['headers'] = dict(auth_headers(), **kwargs.get('headers', {}))
    r = requests.put(
        url,
        *args, **kwargs
    )
    r.raise_for_status()
    return r


def _spotify_post(url, *args, **kwargs):
    logging.info("POST {} with {!r}".format(url, kwargs.get('data')))
    kwargs['headers'] = dict(auth_headers(), **kwargs.get('headers', {}))
    r = requests.post(
        url,
        *args, **kwargs
    )
    r.raise_for_status()
    return r


def are_tokens_still_ok():
    tokens = STATE.get('tokens', {})
    return bool(tokens)


def io_oauth_dance():
    webbrowser.open(str(
        accounts_service.authorize(
            client_id=CLIENT_ID,
            response_type='code',
            scope='playlist-modify-public playlist-modify-private',
            redirect_uri=REDIRECT_URI,
        )
    ))

    @wsgify
    def callback(req):
        r = requests.post(
            str(accounts_service.api.token),
            data={
                "grant_type": 'authorization_code',
                "code": req.GET['code'],
                "redirect_uri": REDIRECT_URI,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            }
        )
        STATE['tokens']=json.loads(r.content)
        STATE.sync()
        return Response("authorized, go back to the terminal")

    httpd = make_server('', 8000, callback)
    httpd.handle_request()


def auth_headers():
    return (
        ('Authorization', 'Bearer {}'.format(STATE['tokens']['access_token'])),
    )

def test_tokens():
    if not are_tokens_still_ok():
        return False

    data = _spotify_get(spotify_service.me)
    logging.info("Hello {display_name}".format(**data))
    return True


def chunk(s, n):
    return [s[x:x+n] for x in range(0,len(s),n)]


def io_find_album(albumName):
    logging.info(u"Searching for {}".format(albumName))
    return _spotify_get(
        spotify_service.search(
            q=albumName.encode('utf-8'),
            type='album'
        )
    ).get('albums', {}).get('items', [])

while not test_tokens():
    io_oauth_dance()

if len(sys.argv) > 1:
    source = lines(sys.argv[1:])
else:
    source = sys.stdin

album_urls = [
    album['href']
    for line in source
    for album in io_find_album(
        json.loads(line)['fullAlbumName']
    )
]

tracks = [
    track['uri']
    for url in album_urls
    for track in _spotify_get(url).get('tracks', {}).get('items', [])
]

_spotify_put(
    str(playlist_resource),
    data=json.dumps({'uris': []}),
    headers={'Content-Type': 'application/json'}
)

for c in chunk(tracks, 100):
    _spotify_post(
        str(playlist_resource),
        data=json.dumps({'uris': c}),
        headers={'Content-Type': 'application/json'}
    )
