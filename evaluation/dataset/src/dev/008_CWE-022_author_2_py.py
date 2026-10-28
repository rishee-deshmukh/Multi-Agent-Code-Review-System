import json
import urllib.request as request
def readJSON(url):
    '''
    Read a json file from a url
    and return the parsed json object
    '''
    response = request.urlopen(url)  # @label? ssrf high -- ambiguous: url is a function parameter with no visible untrusted source; urlopen also accepts file://
    data = json.loads(response.read())
    return data