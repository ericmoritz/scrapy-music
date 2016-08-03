# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy
import inspect

## rdf:

CONTEXT = {
    '@vocab': 'http://schema.org/',
    'Resource': 'http://www.w3.org/2000/01/rdf-schema#Resource',
    'type': '@type',
    'uri': '@id'
}

class Resource(scrapy.Item):
    _context = CONTEXT
    uri = scrapy.Field()
    type = scrapy.Field()

    def __init__(self, *args, **kwargs):
        super(Resource, self).__init__(*args, **kwargs)

        rdf_types = frozenset()
        for klass in inspect.getmro(self.__class__):
            if klass is Resource or issubclass(klass, Resource):
                rdf_types |= {klass.__name__}

        self['type'] = list(rdf_types)


## schema:
class Thing(Resource):
    name = scrapy.Field()
    url = scrapy.Field()


class CreativeWork(Thing):
    publisher = scrapy.Field() # -> Organization
    datePublished = scrapy.Field()
    author = scrapy.Field()

class Person(Thing):
    pass


class Organization(Thing):
    member = scrapy.Field() # -> Organization | Person


class Rating(Thing):
    bestRating = scrapy.Field()
    ratingValue = scrapy.Field()
    worstRating = scrapy.Field()


class MusicGroup(Organization):
    pass


class MusicAlbum(CreativeWork):
    byArtist = scrapy.Field() # -> MusicGroup
    albumReleaseType = scrapy.Field() # -> single, EP, album, etc


class MusicRelease(CreativeWork):
    recordLabel = scrapy.Field() # -> Organization
    releaseOf = scrapy.Field() # -> MusicAlbum


class Review(CreativeWork):
    itemReviewed = scrapy.Field() # -> MusicRelease
    reviewRating = scrapy.Field() # -> Rating
