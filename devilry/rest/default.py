from devilry.dataconverter.jsondataconverter import JsonDataConverter
from devilry.dataconverter.xmldataconverter import XmlDataConverter
from devilry.dataconverter.yamldataconverter import YamlDataConverter
from htmldataconverter import HtmlDataConverter
import inputdata_handlers
import responsehandlers
import restmethod_roters


SUFFIX_TO_CONTENT_TYPE_MAP = {
    "xml": "application/xml",
    "yaml": "application/yaml",
    "json": "application/json",
    "html": "text/html"
}

INPUTDATA_HANDLERS = [
    inputdata_handlers.getqrystring_inputdata_handler,
    inputdata_handlers.rawbody_inputdata_handler
]
DATACONVERTERS = {
    "application/xml": XmlDataConverter,
    "application/yaml": YamlDataConverter,
    "application/json": JsonDataConverter,
    "text/html": HtmlDataConverter
}
RESTMETHOD_ROUTES = [
    restmethod_roters.post_to_create,
    restmethod_roters.get_with_id_to_read,
    restmethod_roters.put_with_id_to_update,
    restmethod_roters.delete_to_delete,
    restmethod_roters.get_without_id_to_list,
    restmethod_roters.put_without_id_to_batch
]
RESPONSEHANDLERS = [
    responsehandlers.stricthttp
]
