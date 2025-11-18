# coding: utf-8
import argparse
import json
import os
thisdir = os.path.abspath(os.path.dirname(__file__))
import re
import string
import urllib


import cherrypy
# Import mimetypes after cherrypy since cherrypy.lib.static inits it.
import mimetypes
mimetypes.types_map['.woff'] = 'application/font-woff'
mimetypes.types_map['.ttf'] = 'application/font-sfnt'


from metaphrase import abspath, auth, libraries, FileNotFound

days1 = 86400


def url(*args, **kwargs):
    """Call url with the given args, kwargs. Quote as needed."""
    s, l, path, q, f = urllib.parse.urlsplit(cherrypy.url(*args, **kwargs))
    path = "/".join([urllib.parse.quote(p) for p in path.split("/")])
    return urllib.parse.urlunsplit((s, l, path, q, f))


def auth_version(role='reader', versions=None, version=None):
    """Return the requested Version, or raise 403 if role is not met.

    If the version is locked and the role is 'writer' or greater, raise 409.
    """
    req = cherrypy.request
    if versions is None:
        versions = library.versions
    if version is None:
        version = req.version
    if not versions.permit(version, req.login, role):
        raise cherrypy.HTTPError(403)

    if libraries.roles[role] >= libraries.roles['writer']:
        if versions.auth.get(version, {}).get("locked", False):
            raise cherrypy.HTTPError(409, "Cannot write. This version is locked.")

    return versions[version]


# ----------------------------------- API ----------------------------------- #


class LexicalNote:
    """/api/versions/{version}/notes/lexical/{lemma}/"""

    exposed = True

    def GET(self):
        req = cherrypy.serving.request
        version = auth_version()

        try:
            note = version.lexical_notes[req.lemma]
        except KeyError:
            cherrypy.response.status = 404
            return {}

        return {
            "self": url(),
            "element": "shoji:entity",
            "body": {
                "note": note
            }
        }

    @cherrypy.tools.json_in()
    def PUT(self):
        """Add or replace a lexical note for the given version and lemma."""
        req = cherrypy.serving.request
        version = auth_version('writer')
        version.lexical_notes[req.lemma] = req.json["body"]["note"]
        version.save_lexical_notes()

        cherrypy.response.status = 204

    def DELETE(self):
        """Delete any lexical note for the given version and lemma."""
        req = cherrypy.serving.request
        version = auth_version('writer')
        try:
            del version.lexical_notes[req.lemma]
            version.save_lexical_notes()
            cherrypy.response.status = 204
        except KeyError:
            cherrypy.response.status = 404


class LexicalNotes:
    """/api/versions/{version}/notes/lexical/"""

    exposed = True

    @cherrypy.tools.expires(secs=days1)
    def GET(self):
        version = auth_version()
        return {
            "self": url(),
            "element": "shoji:catalog",
            "description": (
                "A collection of notes for each lemma. "
                "GET a Note by lemma, PUT a Note to create or replace, "
                "or DELETE."),
            "index": dict(
                (url(k + "/"), {})
                for k, v in sorted(version.lexical_notes.items())
            )
        }

    def _cp_dispatch(self, vpath):
        cherrypy.request.lemma = vpath.pop(0)
        return LexicalNote()


class VersionNotes:
    """/api/versions/{version}/notes/"""

    exposed = True
    lexical = LexicalNotes()

    @cherrypy.tools.expires(secs=days1)
    def GET(self):
        return {
            "self": url(),
            "element": "shoji:catalog",
            "catalogs": {
                "lexical": url("lexical/"),
            }
        }


class ConcordanceEntry:
    """/api/versions/{version}/concordance/{criteria}/{?strict,versions,context}"""

    exposed = True

    def GET(self, strict=False, versions=None, context=6):
        req = cherrypy.serving.request

        versions = [v for v in (versions or "").split(",") if v]
        try:
            context = int(context)
        except (TypeError, ValueError):
            context = 6

        try:
            criteria = libraries.normalize(json.loads(req.criteria))
        except json.JSONDecodeError:
            raise cherrypy.HTTPError(404, "Concordance criteria MUST be valid JSON")

        entries, passages, complete = library.concordance(
            versions, criteria, req.version, bool(strict), context)

        response = {
            "self": url(qs=cherrypy.request.query_string),
            "element": "shoji:entity",
            "body": {
                "passages": passages,
                # This is a {version: {lemma: ...}} tree.
                "entries": entries,
                "complete": complete
            }
        }

        # Collect parents and children.
        # This was migrated from the old lexicon view, which only ever
        # showed one lemma or wordform.
        # TODO: expand to show multiple trees, or move it to somewhere
        # in the API/UI that is more appropriate.
        # Eventually, the concept of "family" should be in the lexicon instead.
        if not isinstance(criteria, list):
            criteria = [criteria]

        lemmas = set([wf["lemma"] for wf in criteria
                      if isinstance(wf, dict) and "lemma" in wf
                      and isinstance(wf["lemma"], str)])
        if len(lemmas) == 1:
            response["body"]["family"] = library.family(lemmas.pop())

        return response


class ConcordanceIndex:
    """/api/versions/{version}/concordance/"""

    exposed = True

    @cherrypy.tools.expires(secs=days1)
    def GET(self, **kwargs):
        version = auth_version()
        return {
            "self": url(qs=cherrypy.request.query_string),
            "element": "shoji:catalog",
            "index": dict(
                (url(k + "/"), {"count": v})
                for k, v in version.word_counts().items()
            )
        }

    def _cp_dispatch(self, vpath):
        cherrypy.request.criteria = vpath.pop(0)
        return ConcordanceEntry()


class MechanicalTranslation:
    """/api/versions/{version}/text/{work}/{section}/translation/"""

    exposed = True

    @cherrypy.tools.json_out()
    def GET(self):
        req = cherrypy.serving.request
        version = auth_version('reader')
        try:
            section = version.load_section(req.workid, req.sectionid)
        except FileNotFound:
            raise cherrypy.NotFound()

        new_ids, new_text = section.translation(version)

        return {"ids": new_ids, "text": new_text}


class WordOrder:
    """/api/versions/{version}/text/{work}/{section}/order/"""

    exposed = True

    @cherrypy.tools.json_in()
    def PATCH(self):
        """Apply the given {id, movebefore} patch document."""
        req = cherrypy.serving.request
        id = req.json["id"]
        movebefore = req.json["movebefore"]

        version = auth_version('writer')
        try:
            section = version.load_section(req.workid, req.sectionid)
            section.move_before(id, movebefore)
            version.save_section(section)
        except ValueError as exc:
            raise cherrypy.HTTPError(400, exc.args[0])

        cherrypy.response.status = 204


class TextSection:
    """/api/versions/{version}/text/{work}/{section}/"""

    exposed = True
    order = WordOrder()
    translation = MechanicalTranslation()

    def GET(self, versions=None):
        """Return an ordered catalog of text entries."""
        req = cherrypy.serving.request
        version = auth_version()

        prev_section = None
        next_section = None
        try:
            section = version.load_section(req.workid, req.sectionid)
        except FileNotFound:
            raise cherrypy.NotFound()

        # Calculate prev, next sections
        ids, names = [], []
        for workid in version.worksorder:
            work = version.works[workid]
            for sectionid in work["sections"]:
                ids.append((workid, sectionid))
                names.append((work.get("name", workid), sectionid))
        try:
            i = ids.index((req.workid, req.sectionid))
        except ValueError:
            pass
        else:
            if i > 0:
                prev_section = {
                    "id": "/".join(ids[i - 1]),
                    "name": " ".join(names[i - 1])
                }
            if i < (len(ids) - 1):
                next_section = {
                    "id": "/".join(ids[i + 1]),
                    "name": " ".join(names[i + 1])
                }

        workname = version.works[req.workid].get("name", req.workid)
        return {
            "self": url(),
            "element": "shoji:catalog",
            "version": req.version,
            "name": " ".join((workname, req.sectionid)),  # TODO: allow names per version
            "previous": prev_section,
            "next": next_section,
            "order": section.order,
            "index": section.entries
        }

    @cherrypy.tools.json_in()
    def PATCH(self):
        """Apply the given catalog patch document."""
        req = cherrypy.serving.request
        version = auth_version('writer')
        try:
            section = version.load_section(req.workid, req.sectionid)
        except FileNotFound:
            raise cherrypy.NotFound()

        section.update(libraries.normalize(req.json["index"]))
        version.save_section(section)

        cherrypy.response.status = 204

    @cherrypy.tools.json_in()
    def POST(self):
        """Accept the given text, tokenize it, and append as new words."""
        req = cherrypy.serving.request
        version = auth_version('writer')

        proposed_text = libraries.normalize(req.json["body"]["text"])
        proposed_text = [
            t.strip()
            for t in re.split(r'(\W+)', proposed_text, flags=re.UNICODE)
            if t.strip()
        ]

        # Look up any existing section.
        try:
            section = version.load_section(req.workid, req.sectionid)
        except FileNotFound:
            section = libraries.Section(req.version, req.workid, req.sectionid)

        # Apply morphology as best we can.
        # Grab a map from original -> most common morphology
        # from the given other work
        lexv = req.json["body"].get("lexicon", None)
        if lexv is None:
            lexv = version
        else:
            lexv = library.versions[lexv]
        morph_map = lexv.morphology_map()

        # Assume an id scheme of work/section/x.y, where we increment 'x' by 1
        # for this set of text as a whole, and assign each word a 'y'
        # from 1 to len(text).
        verses = [id.split(".", 1)[0] for id in section.order]
        x = max([int(v) for v in verses if v.isdigit()] or [0]) + 1
        y = 0

        with section.lock:
            for word in proposed_text:
                y += 1

                verse_number = word.strip(string.punctuation)
                if verse_number.isdigit():
                    # Interpret this as a verse marker. Unfortunately, this means
                    # that text like "he bought 5 jars" may be marked incorrectly.
                    # To combat that, we only change x if it is incrementing.
                    verse_number = int(verse_number)
                    if verse_number == x + 1 or (x == verse_number == 1 and not section.order):
                        x = verse_number
                        y = 0
                        continue

                phraseid = "%s.%s" % (x, y)
                section.order.append("%s:0" % phraseid)
                section.entries[phraseid] = {
                    "parsing": "---------",
                    "lemma": "",
                    "original": word,
                    "text": [word]
                }

                match = morph_map.get(word, None)
                if match:
                    section.entries[phraseid].update(match)

            section.indices = section.calc_indices()
            version.save_section(section)

        cherrypy.response.status = 204


class Text:
    """/api/versions/{version}/text/"""

    exposed = True

    @cherrypy.tools.json_in()
    def PATCH(self):
        """Apply the given {ids, text, lexicon} patch document."""
        req = cherrypy.serving.request
        version = auth_version('writer')

        # Bucket the words so we can load each affected section in order.
        # and also to fail the whole operation if any section cannot be found.
        index = libraries.normalize(req.json['index'])

        by_section = {}
        for id, entry in index.items():
            workid, sectionid, phraseid = id.split("/", 3)
            by_section.setdefault((workid, sectionid), {})[phraseid] = entry

        for (workid, sectionid), patches in by_section.items():
            section = version.load_section(workid, sectionid)
            section.update(patches)
            version.save_section(section)

        cherrypy.response.status = 204

    def _cp_dispatch(self, vpath):
        req = cherrypy.serving.request
        req.workid = vpath.pop(0)
        req.sectionid = vpath.pop(0)

        if vpath or (req.method != "POST"):
            version = library.versions[req.version]
            if req.sectionid not in version.works.get(req.workid, {"sections": []})["sections"]:
                raise cherrypy.NotFound()

        return TextSection()


class LexiconEntries:
    """/api/versions/{version}/lexicon/"""

    exposed = True

    @cherrypy.tools.expires(secs=days1)
    def GET(self, **kwargs):
        req = cherrypy.request
        version = auth_version()
        return {
            "self": url(qs=req.query_string),
            "element": "shoji:catalog",
            # TODO: make this configurable
            "collation": greek_collation,
            "index": dict(
                (urllib.parse.quote(k) + "/", {"count": v})
                for k, v in version.lemma_counts().items()
            )
        }


greek_collation = {
    "Α": ["Ἀ", "Ἁ", "Ἄ", "Ἅ", "Ἆ"],
    "Ε": ["Ἐ", "Ἑ", "Ἔ", "Ἕ"],
    "Η": ["Ἠ", "Ἡ", "Ἤ"],
    "Ι": ["Ἰ", "Ἱ"],
    "Ο": ["Ὀ"],
    "Ρ": ["Ῥ"],
    "Υ": ["Ὑ"],
    "Ω": ["Ὡ", "Ὦ"],

    "α": ["ά", "ἀ", "ἁ", "ἄ", "ἅ", "ἆ", "ᾄ", "ᾅ", "ᾳ", "ᾴ", "ᾶ"],
    "ε": ["έ", "ἐ", "ἑ", "ἔ", "ἕ"],
    "η": ["ή", "ἠ", "ἡ", "ἤ", "ἥ", "ἦ", "ἧ", "ῃ", "ῄ", "ῆ", "ῇ"],
    "ι": ["ί", "ΐ", "ϊ", "ἰ", "ἱ", "ἴ", "ἵ", "ἶ", "ἷ", "ῖ"],
    "ο": ["ό", "ὀ", "ὁ", "ὄ", "ὅ"],
    "ρ": ["ῥ"],
    "σ": ["ς"],
    "υ": ["ΰ", "ϋ", "ύ", "ὐ", "ὑ", "ὔ", "ὕ", "ὖ", "ὗ", "ῦ"],
    "ω": ["ώ", "ὠ", "ὡ", "ὥ", "ὦ", "ὧ", "ᾠ", "ῳ", "ῴ", "ῶ", "ῷ"],
}


class Version:
    """/api/versions/{version}/"""

    exposed = True
    lexicon = LexiconEntries()
    text = Text()
    concordance = ConcordanceIndex()
    notes = VersionNotes()

    @cherrypy.tools.expires(secs=days1)
    def GET(self):
        version = auth_version()
        return {
            "self": url(),
            "element": "shoji:catalog",
            "catalogs": {
                "text": url("text/"),
                "concordance": url("concordance/"),
                "notes": url("notes/"),
            },
            "order": [workid + "/" for workid in version.worksorder],
            "index": dict((workid + "/", work) for workid, work in version.works.items())
        }

    @cherrypy.tools.json_in()
    def PATCH(self):
        version = auth_version('writer')
        req = cherrypy.request

        new_works = libraries.normalize(req.json["index"])
        # TODO: validation
        for workurl, work in new_works.items():
            workid = workurl.split("/")[-2]
            if work is None:
                version.destroy_work(workid)
            else:
                if workid in version.works:
                    if "name" in work:
                        version.works[workid]["name"] = work["name"]
                else:
                    version.works[workid] = {
                        "name": work.get("name", workid),
                        "sections": []
                    }
                    version.worksorder.append(workid)
                existing_sections = version.works[workid]["sections"]

                for sectionid in set(work["sections"]) - set(existing_sections):
                    # Make new (empty) sections
                    s = libraries.Section(version.name, workid, sectionid)
                    version.save_section(s)

        version.save_works()
        cherrypy.response.status = 204

    @cherrypy.tools.json_in()
    def POST(self):
        """Copy works/sections from another version to this one."""
        versions = library.versions
        version = auth_version('writer')
        req = cherrypy.request
        body = req.json["body"]

        parent = body["parent"]
        # TODO: do we need a permission for forking?
        if not versions.permit(parent, req.login, 'reader'):
            raise cherrypy.HTTPError(403)

        works = body.get("works", None)
        if works is not None:
            works = dict((k.split("/")[-2], v) for k, v in works.items())
        versions.copy_sections(versions[parent], version, works,
                               body.get("translate", False))

        cherrypy.response.status = 204

    def DELETE(self):
        version = auth_version('admin')
        library.versions.destroy_version(version)
        cherrypy.response.status = 204


class Versions:
    """/api/versions/"""

    exposed = True

    @cherrypy.tools.expires(secs=days1)
    def GET(self):
        req = cherrypy.request

        # TODO: this needs to be cached in a user object
        # when the number of versions grows large.
        versions = library.versions

        index = {}
        for name in versions.version_names:
            vauth = versions.auth[name]
            if versions.permit(name, req.login, 'reader'):
                k = url(name + "/")

                # Allow admins to see (and change) permissions.
                if versions.permit(name, req.login, 'admin'):
                    perms = vauth["permissions"]
                else:
                    # Only return this user's perms.
                    # This hints to UI's what capabilities to show.
                    perms = vauth["permissions"].get(req.login, None)
                    if perms is not None:
                        perms = {req.login: perms}
                index[k] = {
                    'auth': {
                        "permissions": perms,
                        "locked": vauth["locked"]
                    },
                    'notes': versions[name].version_notes
                }

        payload = {
            "self": url(),
            "element": "shoji:catalog",
            "index": index,
            # Bit of a hack here for auth
            "username": req.login
        }

        cherrypy.response.headers["Vary"] = "Cookie"

        return payload

    @cherrypy.tools.json_in()
    def PATCH(self):
        req = cherrypy.request
        versions = library.versions

        for url, attrs in libraries.normalize(req.json["index"]).items():
            name = url.split("/")[-2]

            if (
                # Anyone can add a version (with themselves as admin)...
                (name not in versions.auth) or
                # but only admins can change permissions...
                versions.permit(name, req.login, 'admin')
            ):
                auth = attrs.get("auth", {})
                to_version = versions[name]

                if name not in versions.version_names:
                    versions.version_names.append(name)
                    to_version.save_works()

                # ...but they cannot remove themself as an admin.
                auth.setdefault("permissions", {})[req.login] = "admin"
                auth.setdefault("locked", False)
                versions.auth[name] = auth

                if "notes" in attrs:
                    v = versions[name]
                    if v.version_notes != attrs["notes"]:
                        v.version_notes = attrs["notes"]
                        v.save_version_notes()

        library.save_auth()
        cherrypy.response.status = 204

    def _cp_dispatch(self, vpath):
        cherrypy.request.version = v = vpath.pop(0)
        if v not in library.versions.version_names:
            raise cherrypy.NotFound()
        return Version()


class API:
    """/api/"""

    exposed = True
    _cp_config = {
        "tools.json_out.on": True,
        "request.is_index": True,
        "request.methods_with_bodies": ("POST", "PUT", "PATCH"),
    }

    login = auth.Login()
    versions = Versions()

    @cherrypy.tools.expires(secs=days1)
    def GET(self):
        return {
            "self": url(),
            "element": "shoji:catalog",
            "catalogs": {
                "versions": url("versions/")
            },
            "login": url("login/")
        }


# ----------------------------------- UI ----------------------------------- #


class ConcordanceEntryUI:
    """/versions/{version}/concordance/{criteria}/"""

    def index(self, **kwargs):
        return open(abspath(thisdir, "ui", "entry.html"), "rb")
    index.exposed = True


class ConcordanceIndexUI:
    """/versions/{version}/concordance/"""

    def index(self, **kwargs):
        return open(abspath(thisdir, "ui", "concordance.html"), "rb")
    index.exposed = True

    def _cp_dispatch(self, vpath):
        criteria = vpath.pop(0)
        return ConcordanceEntryUI()


class VersionUI:
    """/versions/{version}/"""

    concordance = ConcordanceIndexUI()

    def index(self, **kwargs):
        return open(abspath(thisdir, "ui", "version.html"), "rb")
    index.exposed = True


class VersionsUI:
    """/versions/"""

    def index(self, **kwargs):
        return open(abspath(thisdir, "ui", "versions.html"), "rb")
    index.exposed = True

    def _cp_dispatch(self, vpath):
        version = vpath.pop(0)
        return VersionUI()


class SectionUI:
    """/{work}/{section}/"""

    def index(self, **kwargs):
        return open(abspath(thisdir, "ui", "section.html"), "rb")
    index.exposed = True


class WorkUI:
    """/{work}/"""

    def index(self, **kwargs):
        return open(abspath(thisdir, "ui", "work.html"), "rb")
    index.exposed = True

    def _cp_dispatch(self, vpath):
        req = cherrypy.serving.request
        req.sectionid = vpath.pop(0)
        return SectionUI()


class Root:
    """/"""

    api = API()
    versions = VersionsUI()
    ui = cherrypy.tools.staticdir.handler(
        section="/ui", dir="ui", root=thisdir)

    _cp_config = {
        '/ui': {
            "tools.expires.on": True,
            "tools.expires.secs": days1,
        }
    }

    @cherrypy.tools.expires(secs=days1)
    def index(self, **kwargs):
        return open(abspath(thisdir, "ui", "root.html"), "rb")
    index.exposed = True

    def healthy(self):
        return "OK"
    healthy.exposed = True
    healthy._cp_config = {"tools.auth_basic.on": False}

    def _cp_dispatch(self, vpath):
        cherrypy.request.work = vpath.pop(0)
        return WorkUI()


library = None


def configure(libpath, domain, port, proxied):
    global library
    library = libraries.Library(os.path.abspath(os.path.expanduser(libpath)))
    auth.cookie_domain = domain

    return {
        "global": {
            "server.socket_host": "0.0.0.0",
            "server.socket_port": port,
            "checker.on": False,
            "log.error_file": "metaphrase-error.log"
        },
        '/': {
            'tools.token_auth.on': True,
            'tools.token_auth.secure': proxied,
            'tools.proxy.on': proxied,
            # 'tools.proxy.debug': True,
        },
        "/api": {
            "request.dispatch": cherrypy.dispatch.MethodDispatcher()
        }
    }


cl_arg_parser = argparse.ArgumentParser(description="Serve a Metaphrase site.")
cl_arg_parser.add_argument(
    '--library', dest='libpath', action='store', required=True,
    help='The root directory for storing works.'
    )
cl_arg_parser.add_argument(
    '--domain', dest='domain', action='store', type=str, default="metaphrase.org",
    help='Cookie domain.'
    )
cl_arg_parser.add_argument(
    '--port', dest='port', action='store', type=int, default=8374,
    help='Port to listen on.'
    )
cl_arg_parser.add_argument(
    '--proxy', dest='proxy', action='store_true',
    help='Turn on proxying to fix up emitted URIs.'
    )


def main():
    args = cl_arg_parser.parse_args()
    conf = configure(args.libpath, args.domain, args.port, args.proxy)
    cherrypy.quickstart(Root(), '/', conf)


if __name__ == '__main__':
    main()
