from scrapy.exporters import JsonLinesItemExporter
from scrapy.utils.python import to_bytes


class JsonLDLinesItemExporter(JsonLinesItemExporter):
    def export_item(self, item):
        itemdict = dict(self._get_serialized_fields(item))
        if hasattr(item, '_context'):
            itemdict['@context'] = item._context

        data = self.encoder.encode(itemdict) + '\n'
        self.file.write(to_bytes(data, self.encoding))
