#!/usr/bin/env python
import sys
from rdflib import Graph

g = Graph()
for line in sys.stdin:
    g = g.parse(data=line, format='json-ld')

print g.serialize(format='turtle')
