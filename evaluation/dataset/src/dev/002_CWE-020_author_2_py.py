import xml.etree.ElementTree as ET


def parse_xml(xml_string):
    '''
    Parse xml_string and return the root element of the XML document
    '''
    root = ET.fromstring(xml_string)  # @label xml_parsing medium -- stdlib ElementTree is open to entity-expansion (billion laughs) DoS; no external entity resolution
    return root