# -*- coding: utf-8 -*-
import scrapy
import json
import re
import logging
from music import items

def _music_uri(path):
    return 'tag:eric.moritz@gmail.com,2016:music/{}'.format(path)


def _pitchfork_uri(path):
    return _music_uri('pitchfork.com/{}'.format(path))


class PitchforkSpider(scrapy.Spider):
    name = "pitchfork"
    allowed_domains = ["pitchfork.com"]
    start_urls = (
        'http://pitchfork.com/api/v1/albumreviews/?limit=100&offset=0',
    )

    def parse(self, response):
        data = json.loads(response.body)
        for result in data['results']:

            review_uri =  _pitchfork_uri(
                'review/{}'.format(result['id'])
            )
            release_uris = frozenset()

            for i, album_json in enumerate(result['tombstone']['albums']):
                artists = [
                    items.MusicGroup(
                        uri = _pitchfork_uri('artists/{}'.format(x['id'])),
                        name = x['display_name']
                    )
                    for x in album_json['album']['artists']
                ]
                for x in artists: yield x

                album = items.MusicAlbum(
                    uri = _pitchfork_uri('album/{}'.format(_album_id(album_json))),
                    byArtist = [x['uri'] for x in artists]
                )
                yield album

                rating = items.Rating(
                    uri = review_uri + "#reviewRating",
                    bestRating = 10,
                    worstRating = 0,
                    ratingValue = float(album_json['rating']['rating'])
                )

                labels = [
                    items.Organization(
                        uri=_pitchfork_uri('label/{}'.format(l['id'])),
                        name=l['name']
                    )
                    for x in album_json['labels_and_years']
                    for l in x['labels']
                ]

                for x in labels:
                    yield x

                release = items.MusicRelease(
                    uri = review_uri + '#itemReviewed/{}'.format(i),
                    releaseOf = album['uri'],
                    recordLabel = [l['uri'] for l in labels]
                )
                yield release
                yield items.Review(
                    uri=review_uri,
                    itemReviewed = release['uri'],
                    reviewRating = rating['uri']
                )

def t(val):
    logging.info(repr(val))
    return val


ALBUM_ID_PAT = re.compile('.+/albums/(\d+)')
def _album_id(album_json):
    match = ALBUM_ID_PAT.match(album_json['album']['artwork']['default'])
    if match:
        return match.group(1)
    else:
        raise ValueError("Could not detect album id")
