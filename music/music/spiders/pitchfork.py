# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from decimal import Decimal
import scrapy
import json
import re
import logging
import os
from music import items

RECORDS_NEWER_THAN=os.environ.get(
    'RECORDS_NEWER_THAN',
    (datetime.utcnow().date() - timedelta(days=2)).isoformat()
)

def _music_uri(path):
    return 'tag:eric.moritz@gmail.com,2016:music/{}'.format(path)


def _pitchfork_uri(path):
    return _music_uri('pitchfork.com/{}'.format(path))


class PitchforkSpider(scrapy.Spider):
    name = "pitchfork"
    allowed_domains = ["pitchfork.com"]
    start_urls = (
        'http://pitchfork.com/api/v1/albumreviews/?format=json',
    )

    def parse(self, response):
        data = json.loads(response.body)
        nextPage = data.get('next')
        if nextPage:
            yield scrapy.Request(
                response.urljoin(nextPage),
                callback=self.parse
            )

        publisher = items.Organization(
            uri = "http://pitchfork.com/",
            name = 'Pitchfork'
        )

        for result in data['results']:
            date_published = _date(result['timestamp'])
            if date_published < RECORDS_NEWER_THAN:
                raise scrapy.exceptions.CloseSpider(
                    "{} < {}".format(
                        date_published,
                        RECORDS_NEWER_THAN
                    )
                )


            for i, album_json in enumerate(result['tombstone']['albums']):

                review_uri =  _pitchfork_uri(
                    'review/{}/{}'.format(result['id'],i)
                )

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
                    name = album_json['album']['display_name'],
                    byArtist = [_link(x['uri']) for x in artists]
                )
                yield album

                rating = items.Rating(
                    uri = review_uri + "#reviewRating",
                    bestRating = 1000,
                    worstRating = 0,
                    ratingValue = int(Decimal(album_json['rating']['rating']) * 100)
                )
                yield rating

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
                    releaseOf = _link(album['uri']),
                    recordLabel = [_link(l['uri']) for l in labels]
                )


                yield release
                yield items.Review(
                    uri = review_uri,
                    url = response.urljoin(result['url']),
                    datePublished = date_published,
                    itemReviewed = _link(release['uri']),
                    reviewRating = _link(rating['uri']),
                    publisher = _link(publisher['uri'])
                )


def _date(x):
    return datetime.utcfromtimestamp(x / 1000).isoformat() + 'Z'


def _link(x):
    return {'@id': x}


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
