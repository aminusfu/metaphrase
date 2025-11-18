# coding: utf-8

from base64 import b64encode
import json
import os

import cherrypy
from cherrypy.test import webtest

from metaphrase import root as mph
from metaphrase import auth

thisdir = os.path.dirname(os.path.abspath(__file__))
missing = object()


class MetaphraseTestCase(webtest.WebCase):

    PORT = 8080
    HOST = 'local.metaphrase.org'
    SCRIPT_NAME = '/'

    def base(self):
        if (
            (self.scheme == "http" and self.PORT == 80) or
            (self.scheme == "https" and self.PORT == 443)
        ):
            port = ""
        else:
            port = ":%s" % self.PORT

        return "%s://%s%s" % (self.scheme, self.HOST, port)

    login = "test"

    def getPage(self, url, method='GET', body=None, headers=None, login=missing):
        if headers is None:
            headers = {}
        if isinstance(headers, list):
            headers = dict(headers)

        if login is missing:
            login = self.login
        if login is not None:
            token = auth.tokens[login]
            headers.setdefault(
                "Cookie", 'login="%s"; token=%s' % (b64encode(login).decode("latin1"), token)
            )

        return webtest.WebCase.getPage(
            self, url, method=method, body=body, headers=headers.items())

    @property
    def json(self):
        return json.loads(self.body)

    def get_text(self, indices):
        j = self.json
        output = []
        for i in indices:
            phraseid, wordid = j["order"][i].split(":", 1)
            output.append(j["index"][phraseid]["text"][int(wordid)])
        return output

    def assertJSON(self, expected):
        self.assertEqual(self.json, expected)

    def POST_json(self, url, payload):
        body = json.dumps(payload)
        headers = [
            ('Content-type', 'application/json'),
            ('Content-length', str(len(body)))
        ]
        return self.getPage(url, method='POST', body=body, headers=headers)

    def PUT_json(self, url, payload):
        body = json.dumps(payload)
        headers = [
            ('Content-type', 'application/json'),
            ('Content-length', str(len(body)))
        ]
        return self.getPage(url, method='PUT', body=body, headers=headers)

    def PATCH_json(self, url, payload, headers=None):
        body = json.dumps(payload)
        if headers is None:
            headers = {}
        if isinstance(headers, list):
            headers = dict(headers)

        for k, v in [
            ('Content-type', 'application/json'),
            ('Content-length', str(len(body)))
        ]:
            headers.setdefault(k, v)

        return self.getPage(url, method='PATCH', body=body, headers=headers.items())

    def patch_word(self, phraseid, atoms, workid="1Co", sectionid="1", version="translated"):
        self.PATCH_json(
            '/api/versions/%s/text/%s/%s/' %
            (version, workid, sectionid),
            {"index": {phraseid: {"text": [atoms] if isinstance(atoms, basestring) else atoms}}}
        )
        self.assertStatus(204)

    def movebefore(self, id, before, workid="1Co", sectionid="1", version="translated"):
        self.PATCH_json(
            '/api/versions/%s/text/%s/%s/order/' %
            (version, workid, sectionid),
            {"id": id, "movebefore": before}
        )
        self.assertStatus(204)


def setUpServer():
    print("--------------------------------- GLOBAL SETUP ---------------------------------")
    cherrypy.config.update({
        "environment": "test_suite",
        # Uncomment the following line to get CP logs output to screen:
        # "log.screen": True,
    })

    # Set some attributes on the Request object in the test thread,
    # so that we can use cherrypy.url() to generate URLs to GET.
    #base = 'http://%s:%s%s' % (self.HOST, self.PORT, self.SCRIPT_NAME)
    mtc = MetaphraseTestCase
    cherrypy.request.app = True
    cherrypy.request.base = "http://%s:%s" % (mtc.HOST, mtc.PORT)
    cherrypy.request.script_name = mtc.SCRIPT_NAME

    # Create a user or two, with tokens.
    auth.set_password('test', 'letmein')
    auth.tokens['test'] = auth.hexlify(auth.urandom(64))
    auth.set_password('nobody', 'noperms')
    auth.tokens['nobody'] = auth.hexlify(auth.urandom(64))

    conf = mph.configure(
        os.path.join(thisdir, 'library'),
        'local.metaphrase.org', mtc.PORT, proxied=False
    )
    cherrypy.tree.mount(mph.Root(), mtc.SCRIPT_NAME, conf)
    cherrypy.engine.signals.subscribe()
    cherrypy.engine.start()


def tearDownServer():
    cherrypy.engine.exit()


def setUpPackage():
    setUpServer()


def tearDownPackage():
    # Unfortunately, a package-level tearDown works until you try
    # to supply more than one file arg to nosetests, in which case
    # tearDownPackage() is called after the first path is done (!)
    # and won't be called again.
    #
    # This will shut down cherrypy and our tests aren't designed to start
    # it back up in between each test class.
    #
    # In addition, your test run will hang if any test class after
    # the first starts up cherrypy, because this tear down will not
    # be executed again at the end of the run, and cherrypy will
    # wait forever for nose to tell it to shut down, while nose
    # will wait forever for cherrypy to shut down.
    # The only way to pass multiple path args to nose, therefore,
    # is to make a tearDownClass method that calls cherrypy.engine.stop.
    # We're printing this banner message to help alert you to this fact
    # when you pass multiple path args to nose.
    print("--------------------------------- GLOBAL TEARDOWN ---------------------------------")
    tearDownServer()
