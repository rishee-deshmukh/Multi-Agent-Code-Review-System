from lxml import etree


def parse_invoice(xml_bytes: bytes):
    parser = etree.XMLParser(resolve_entities=True, no_network=False, load_dtd=True)
    root = etree.fromstring(xml_bytes, parser)
    return {
        "number": root.findtext("number"),
        "total": root.findtext("total"),
        "lines": [li.findtext("sku") for li in root.findall("lines/line")],
    }
