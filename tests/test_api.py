# coding: utf-8
from copy import deepcopy
import urllib

from . import MetaphraseTestCase


class TestBasicNav(MetaphraseTestCase):

    def test_root(self):
        self.getPage('/api/')
        self.assertStatus(200)
        self.assertJSON({
            "self": "http://local.metaphrase.org:8080/api/",
            "element": "shoji:catalog",
            "catalogs": {
                "versions": "http://local.metaphrase.org:8080/api/versions/"
            },
            "login": "http://local.metaphrase.org:8080/api/login/",
        })


class TestVersions(MetaphraseTestCase):

    maxDiff = None

    def test_versions(self):
        self.getPage('/api/versions/')
        self.assertStatus(200)
        url = "http://local.metaphrase.org:8080/api/versions/"
        self.assertJSON({
            "self": url,
            "element": "shoji:catalog",
            "username": "test",
            "index": {
                url + "translated/": {
                    "auth": {
                        "locked": False,
                        "permissions": {"test": "admin"}
                    },
                    'notes': ''
                },
                url + "untranslated/": {
                    "auth": {
                        "locked": False,
                        "permissions": {"test": "admin", "public": "reader"}
                    },
                    'notes': ''
                }
            }
        })

    def test_versions_perms_modify(self):
        self.getPage('/api/versions/')
        self.assertStatus(200)
        index1 = self.json['index']

        # Add public=reader to the translated version.
        url = "http://local.metaphrase.org:8080/api/versions/"
        index2 = deepcopy(index1)
        index2[url + 'translated/']['auth']['permissions']['public'] = "reader"
        self.PATCH_json(
            '/api/versions/',
            {"element": "shoji:catalog", "index": index2}
        )
        self.assertStatus(204)

        self.getPage('/api/versions/')
        self.assertStatus(200)
        index3 = self.json['index']
        self.assertEqual(index3, index2)

        # Remove public=reader from the translated version.
        url = "http://local.metaphrase.org:8080/api/versions/"
        index4 = deepcopy(index3)
        del index4[url + 'translated/']['auth']['permissions']['public']
        self.PATCH_json(
            '/api/versions/',
            {"element": "shoji:catalog", "index": index4}
        )
        self.assertStatus(204)

        self.getPage('/api/versions/')
        self.assertStatus(200)
        index5 = self.json['index']
        self.assertEqual(index5, index1)

    def test_versions_version(self):
        self.getPage('/api/versions/untranslated/')
        self.assertStatus(200)
        self.assertJSON({
            "self": "http://local.metaphrase.org:8080/api/versions/untranslated/",
            "element": "shoji:catalog",
            "catalogs": {
                "concordance": "http://local.metaphrase.org:8080/api/versions/untranslated/concordance/",
                "notes": "http://local.metaphrase.org:8080/api/versions/untranslated/notes/",
                "text": "http://local.metaphrase.org:8080/api/versions/untranslated/text/",
            },
            "order": ["1Co/"],
            "index": {
                "1Co/": {"name": "1 Corinthians", "sections": ["1", "2"]},
            }
        })

    def test_create_delete_version(self):
        self.getPage('/api/versions/')
        self.assertStatus(200)
        self.assertNotIn('momentary', [url.split("/")[-2] for url in self.json["index"]])

        # Add a version.
        self.PATCH_json('/api/versions/', {"index": {"momentary/": {}}})
        self.assertStatus(204)

        # The new version MUST appear in the versions catalog...
        self.getPage('/api/versions/')
        self.assertStatus(200)
        self.assertIn('momentary', [url.split("/")[-2] for url in self.json["index"]])

        # ...and have its own entity
        self.getPage('/api/versions/momentary/')
        self.assertStatus(200)
        self.assertEqual(self.json['self'].split("/")[-2], "momentary")

        self.getPage('/api/versions/momentary/', method="DELETE")
        self.assertStatus(204)
        self.getPage('/api/versions/momentary/')
        self.assertStatus(404)

    def test_create_rename_delete_section(self):
        self.PATCH_json(
            '/api/versions/untranslated/', {
            "index": {
                "crds/": {"name": "CRDS", "sections": []}
            }
        })
        self.assertStatus(204)

        self.PATCH_json(
            '/api/versions/untranslated/', {
            "index": {
                "crds/": {"name": "CRDS", "sections": ["1", "2"]}
            }
        })
        self.assertStatus(204)

        self.getPage('/api/versions/untranslated/')
        self.assertStatus(200)
        self.assertJSON({
            "self": "http://local.metaphrase.org:8080/api/versions/untranslated/",
            "element": "shoji:catalog",
            u'catalogs': {
                u'concordance': u'http://local.metaphrase.org:8080/api/versions/untranslated/concordance/',
                u'notes': u'http://local.metaphrase.org:8080/api/versions/untranslated/notes/',
                u'text': u'http://local.metaphrase.org:8080/api/versions/untranslated/text/'
            },
            "order": ["1Co/", "crds/"],
            "index": {
                "1Co/": {"name": "1 Corinthians", "sections": ["1", "2"]},
                "crds/": {"name": "CRDS", "sections": ["1", "2"]}
            }
        })

        self.PATCH_json(
            '/api/versions/untranslated/', {
            "index": {
                "crds/": None
            }
        })
        self.assertStatus(204)
        self.getPage('/api/versions/untranslated/')
        self.assertStatus(200)
        self.assertJSON({
            "self": "http://local.metaphrase.org:8080/api/versions/untranslated/",
            "element": "shoji:catalog",
            u'catalogs': {
                u'concordance': u'http://local.metaphrase.org:8080/api/versions/untranslated/concordance/',
                u'notes': u'http://local.metaphrase.org:8080/api/versions/untranslated/notes/',
                u'text': u'http://local.metaphrase.org:8080/api/versions/untranslated/text/'
            },
            "order": ["1Co/"],
            "index": {
                "1Co/": {"name": "1 Corinthians", "sections": ["1", "2"]},
            }
        })

    def test_version_section_text(self):
        self.getPage('/api/versions/untranslated/text/1Co/1/')
        self.assertStatus(200)
        self.assertEqual(
            self.get_text(xrange(3)),
            [
                u'\u03a0\u03b1\u1fe6\u03bb\u03bf\u03c2',
                u'\u03ba\u03bb\u03b7\u03c4\u1f78\u03c2',
                u'\u1f00\u03c0\u03cc\u03c3\u03c4\u03bf\u03bb\u03bf\u03c2'
            ]
        )

    def test_lexicon_entry_count(self):
        self.getPage('/api/versions/translated/lexicon/')
        self.assertStatus(200)
        self.assertEqual(
            self.json["collation"][u"\u03a9"], [u"\u1f69", u"\u1f6e"]
        )
        self.assertEqual(
            self.json["index"]["%CE%BC%CE%B7%CE%B4%CE%B5%CE%AF%CF%82/"],
            {"count": 1}
        )

    def test_lexicon(self):
        self.getPage('/api/versions/translated/text/1Co/1/')
        self.assertStatus(200)
        self.assertEqual(
            self.json["index"]['1.1'],
            {
                'lemma': u'\u03a0\u03b1\u1fe6\u03bb\u03bf\u03c2',
                'original': u'\u03a0\u03b1\u1fe6\u03bb\u03bf\u03c2',
                'parsing': 'N----NSM-',
                'text': [u'Paul']
            }
        )

        # Alter.
        self.PATCH_json(
            '/api/versions/translated/text/1Co/1/', {
                "index": {
                    "1.1": {
                        'lemma': u'\u03a0\u03b1\u1fe6\u03bb\u03bf\u03c2?',
                        'parsing': 'N----NSFW'
                    }
                }
            }
        )
        self.assertStatus(204)

        self.getPage('/api/versions/translated/text/1Co/1/')
        self.assertStatus(200)
        self.assertEqual(
            self.json["index"]['1.1'],
            {
                'lemma': u'\u03a0\u03b1\u1fe6\u03bb\u03bf\u03c2?',
                # Unchanged
                'original': u'\u03a0\u03b1\u1fe6\u03bb\u03bf\u03c2',
                'parsing': 'N----NSFW',
                'text': [u'Paul']
            }
        )

        # Revert.
        self.PATCH_json(
            '/api/versions/translated/text/1Co/1/', {
                "index": {
                    "1.1": {
                        'lemma': u'\u03a0\u03b1\u1fe6\u03bb\u03bf\u03c2',
                        'parsing': 'N----NSM-',
                    }
                }
            }
        )
        self.assertStatus(204)

        self.getPage('/api/versions/translated/text/1Co/1/')
        self.assertStatus(200)
        self.assertEqual(
            self.json["index"]['1.1'],
            {
                'lemma': u'\u03a0\u03b1\u1fe6\u03bb\u03bf\u03c2',
                'original': u'\u03a0\u03b1\u1fe6\u03bb\u03bf\u03c2',
                'parsing': 'N----NSM-',
                'text': [u'Paul']
            }
        )

    def test_PATCH_lexicon_entire_text(self):
        self.getPage('/api/versions/translated/text/1Co/1/')
        self.assertStatus(200)
        self.assertEqual(
            self.json["index"]['1.1'],
            {
                'lemma': u'\u03a0\u03b1\u1fe6\u03bb\u03bf\u03c2',
                'original': u'\u03a0\u03b1\u1fe6\u03bb\u03bf\u03c2',
                'parsing': 'N----NSM-',
                'text': [u'Paul']
            }
        )

        # Alter by PATCHing the entire text/
        self.PATCH_json(
            '/api/versions/translated/text/', {
                "index": {
                    "1Co/1/1.1": {
                        'lemma': u'\u03a0\u03b1\u1fe6\u03bb\u03bf\u03c2?',
                        'parsing': 'N----NSFW'
                    }
                }
            }
        )
        self.assertStatus(204)

        self.getPage('/api/versions/translated/text/1Co/1/')
        self.assertStatus(200)
        self.assertEqual(
            self.json["index"]['1.1'],
            {
                'lemma': u'\u03a0\u03b1\u1fe6\u03bb\u03bf\u03c2?',
                # Unchanged
                'original': u'\u03a0\u03b1\u1fe6\u03bb\u03bf\u03c2',
                'parsing': 'N----NSFW',
                'text': [u'Paul']
            }
        )

        # Revert.
        self.PATCH_json(
            '/api/versions/translated/text/', {
                "index": {
                    "1Co/1/1.1": {
                        'lemma': u'\u03a0\u03b1\u1fe6\u03bb\u03bf\u03c2',
                        'parsing': 'N----NSM-'
                    }
                }
            }
        )
        self.assertStatus(204)

        self.getPage('/api/versions/translated/text/1Co/1/')
        self.assertStatus(200)
        self.assertEqual(
            self.json["index"]['1.1'],
            {
                'lemma': u'\u03a0\u03b1\u1fe6\u03bb\u03bf\u03c2',
                'original': u'\u03a0\u03b1\u1fe6\u03bb\u03bf\u03c2',
                'parsing': 'N----NSM-',
                'text': [u'Paul']
            }
        )


class TestNoPermsNav(MetaphraseTestCase):

    login = "nobody"
    maxDiff = None

    def test_versions_perms(self):
        url = "http://local.metaphrase.org:8080/api/versions/"
        self.getPage(url)
        self.assertJSON({
            "self": url,
            "element": "shoji:catalog",
            "username": "nobody",
            # The 'nobody' user has no perms on any version;
            # however, the "public" perms on "untranslated" = 'r'
            "index": {
                url + "untranslated/": {
                    "auth": {"locked": False, "permissions": None},
                    "notes": ""
                },
            }
        })

    def test_update_perms(self):
        # Try to update two words in the untranslated version.
        self.PATCH_json(
            '/api/versions/untranslated/text/1Co/1/',
            {
                "index": {
                    "1.1": {"text": ["Paulos"]},
                    "1.3": {"text": ["an apostle"]}
                }
            }
        )
        # The call MUST fail since the 'nobody' user only has read permission
        # on the untranslated version (and that only through the 'public' user)
        self.assertStatus(403)


class TestText(MetaphraseTestCase):

    def assert_original_text(self):
        self.getPage('/api/versions/translated/text/1Co/1/')
        self.assertStatus(200)
        self.assertEqual(
            self.get_text(xrange(3)),
            [
                u'Paul',
                u'\u03ba\u03bb\u03b7\u03c4\u1f78\u03c2',
                u'apostle'
            ]
        )
        self.assertEqual(self.json['order'][:3], ["1.1:0", "1.2:0", "1.3:0"])

    def test_update_section(self):
        self.assert_original_text()

        # Update two words.
        self.PATCH_json(
            '/api/versions/translated/text/1Co/1/',
            {
                "index": {
                    "1.1": {"text": ["Paulos"]},
                    "1.3": {"text": ["an apostle"]}
                }
            }
        )
        self.assertStatus(204)

        # Assert the changes.
        self.getPage('/api/versions/translated/text/1Co/1/')
        self.assertStatus(200)
        self.assertEqual(
            self.get_text(xrange(3)),
            [
                u'Paulos',
                u'\u03ba\u03bb\u03b7\u03c4\u1f78\u03c2',
                u'an apostle'
            ]
        )
        self.assertEqual(self.json['order'][:3], ["1.1:0", "1.2:0", "1.3:0"])

        # Revert the two words. In reverse order, why not?
        self.PATCH_json(
            '/api/versions/translated/text/1Co/1/',
            {
                "index": {
                    "1.3": {"text": ["apostle"]},
                    "1.1": {"text": ["Paul"]}
                }
            }
        )
        self.assertStatus(204)

        # Assert the reversion.
        self.assert_original_text()

    def test_move_backward(self):
        self.assert_original_text()

        # Move word 3 before word 2
        self.movebefore("1.3:0", "1.2:0")

        # Assert the changes.
        self.getPage('/api/versions/translated/text/1Co/1/')
        self.assertStatus(200)
        self.assertEqual(
            self.get_text(xrange(3)),
            [
                u'Paul',
                u'apostle',
                u'\u03ba\u03bb\u03b7\u03c4\u1f78\u03c2',
            ]
        )
        self.assertEqual(self.json['order'][:3], ["1.1:0", "1.3:0", "1.2:0"])

        # Revert the move
        self.movebefore("1.2:0", "1.3:0")

        # Assert the reversion.
        self.assert_original_text()

    def test_move_forward(self):
        self.assert_original_text()

        # Move word 1 before word 3
        self.movebefore("1.1:0", "1.3:0")

        # Assert the changes.
        self.getPage('/api/versions/translated/text/1Co/1/')
        self.assertStatus(200)
        self.assertEqual(
            self.get_text(xrange(3)),
            [
                u'\u03ba\u03bb\u03b7\u03c4\u1f78\u03c2',
                u'Paul',
                u'apostle',
            ]
        )
        self.assertEqual(self.json['order'][:3], ["1.2:0", "1.1:0", "1.3:0"])

        # Revert the move
        self.movebefore("1.1:0", "1.2:0")

        # Assert the reversion.
        self.assert_original_text()

    def test_update_text(self):
        self.assert_original_text()

        # Update two words by PATCHing the text/ root rather than a section.
        self.PATCH_json(
            '/api/versions/translated/text/',
            {
                "index": {
                    "1Co/1/1.1": {"text": ["Paulos"]},
                    "1Co/1/1.3": {"text": ["an apostle"]}
                }
            }
        )
        self.assertStatus(204)

        # Assert the changes.
        self.getPage('/api/versions/translated/text/1Co/1/')
        self.assertStatus(200)
        self.assertEqual(
            self.get_text(xrange(3)),
            [
                u'Paulos',
                u'\u03ba\u03bb\u03b7\u03c4\u1f78\u03c2',
                u'an apostle'
            ]
        )
        self.assertEqual(self.json['order'][:3], ["1.1:0", "1.2:0", "1.3:0"])

        # Revert the two words. In reverse order, why not?
        self.PATCH_json(
            '/api/versions/translated/text/',
            {
                "index": {
                    "1Co/1/1.3": {"text": ["apostle"]},
                    "1Co/1/1.1": {"text": ["Paul"]}
                }
            }
        )
        self.assertStatus(204)

        # Assert the reversion.
        self.assert_original_text()


class TestSplitText(MetaphraseTestCase):
    # Tests that exercise the mapping of more than one word to each original.

    def assert_original_text(self):
        self.getPage('/api/versions/translated/text/1Co/1/')
        self.assertStatus(200)
        self.assertEqual(
            self.get_text(xrange(3)),
            [
                u'Paul',
                u'\u03ba\u03bb\u03b7\u03c4\u1f78\u03c2',
                u'apostle'
            ]
        )
        self.assertEqual(self.json['order'][:3], ["1.1:0", "1.2:0", "1.3:0"])

    def test_update_split(self):
        self.assert_original_text()

        # Update one word to make it two.
        self.patch_word("1.3", ["an", "apostle"])

        # Assert the changes.
        self.getPage('/api/versions/translated/text/1Co/1/')
        self.assertStatus(200)
        self.assertEqual(
            self.get_text(xrange(4)),
            [u'Paul', u'\u03ba\u03bb\u03b7\u03c4\u1f78\u03c2',
             u'an', u'apostle']
        )
        self.assertEqual(
            self.json['order'][:4],
            ["1.1:0", "1.2:0", "1.3:0", "1.3:1"]
        )

        # Revert the words.
        self.patch_word("1.3", "apostle")
        self.assert_original_text()

    def test_move_backward_split(self):
        self.assert_original_text()

        self.patch_word("2.26", ["of", "lord"])

        # Move "our" so that "of lord our" becomes "of our lord".
        self.movebefore("2.27:0", "2.26:1")

        # Assert the changes.
        self.getPage('/api/versions/translated/text/1Co/1/')
        self.assertStatus(200)
        self.assertEqual(
            self.get_text(xrange(37, 40)),
            [u'of', u'our', u'lord']
        )
        self.assertEqual(
            self.json['order'][37:40],
            ["2.26:0", "2.27:0", "2.26:1"]
        )

        # Revert the move
        self.movebefore("2.26:1", "2.27:0")

        # Assert the reversion.
        self.getPage('/api/versions/translated/text/1Co/1/')
        self.assertStatus(200)
        self.assertEqual(
            self.get_text(xrange(37, 40)),
            [u'of', u'lord', u'our']
        )
        self.assertEqual(
            self.json['order'][37:40],
            ["2.26:0", "2.26:1", "2.27:0"]
        )

        self.patch_word("2.26", "lord")

    def test_move_entire_split(self):
        # This failed in production because popping atom A garbled the
        # position of atom B in the indices() for that word's atoms.
        self.assert_original_text()

        self.patch_word("2.26", ["of", "lord"])

        # Move "lord" so that "of lord our" becomes "of our lord".
        self.movebefore("2.26:1", "2.28:0")

        # Now move "of" so that "of our lord" becomes "our of lord".
        self.movebefore("2.26:0", "2.26:1")

        # Assert the moves.
        self.getPage('/api/versions/translated/text/1Co/1/')
        self.assertStatus(200)
        self.assertEqual(
            self.get_text(xrange(37, 40)),
            [u'our', u'of', u'lord']
        )
        self.assertEqual(
            self.json["order"][37:40],
            ["2.27:0", "2.26:0", "2.26:1"]
        )

        # Now move them both back.
        self.movebefore("2.26:0", "2.27:0")
        self.movebefore("2.26:1", "2.27:0")

        # Assert the moves.
        self.getPage('/api/versions/translated/text/1Co/1/')
        self.assertStatus(200)
        self.assertEqual(
            self.get_text(xrange(37, 40)),
            [u'of', u'lord', u'our']
        )
        self.assertEqual(
            self.json['order'][37:40],
            ["2.26:0", "2.26:1", "2.27:0"]
        )

        self.patch_word("2.26", "lord")


class TestConcordance(MetaphraseTestCase):

    maxDiff = None

    def test_word_counts(self):
        self.getPage("/api/versions/translated/concordance/")
        self.assertStatus(200)
        url = 'http://local.metaphrase.org:8080/api/versions/translated/concordance/God/'
        self.assertEqual(self.json['index'][url], {"count": 31})

    def test_a_wordform(self):
        # Note that the wordform MUST be utf-8
        self.getPage('/api/versions/translated/concordance/{"text":".*God"}/?versions=translated')
        self.assertStatus(200)
        passages = self.json["body"]["passages"]
        self.assertEqual(len(passages), 32)
        self.assertEqual(passages[0], {
            u'phraseid': u'1.8',
            u'wordids': [0],
            u'section': u'1Co/1/',
            u'versions': {
                u'translated': [
                    '1.2:0', '1.3:0', '1.4:0', '1.5:0',
                    '1.6:0', '1.7:0', '1.8:0', '1.9:0',
                    '1.10:0', '1.11:0', '1.12:0', '2.1:0',
                    '2.2:0'
                ]
            }
        })

    def test_strict(self):
        url = ('/api/versions/translated/concordance/' +
               urllib.parse.quote('{"text": "God"}') +
               '/?versions=translated&strict=true')
        self.getPage(url)
        self.assertStatus(200)

        self.assertEqual(self.json['self'], 'http://local.metaphrase.org:8080' + url)
        self.assertEqual(self.json['element'], 'shoji:entity')
        self.assertEqual(len(self.json['body']['passages']), 31)

    def test_multiple_wordforms(self):
        # Note that each wordform MUST be utf-8
        self.getPage('/api/versions/translated/concordance/' +
                     urllib.parse.quote('[{"text": ".*God"}, {"text": ","}]') +
                     '/?versions=translated')
        self.assertStatus(200)
        passages = self.json["body"]["passages"]
        self.assertEqual(len(passages), 8)
        self.assertEqual(passages[0], {
            u'phraseid': u'2.4',
            u'wordids': [0],
            u'section': u'1Co/1/',
            u'versions': {
                u'translated': [
                    '1.10:0', '1.11:0', '1.12:0', '2.1:0',
                    '2.2:0', '2.3:0', '2.4:0', '2.5:0',
                    '2.6:0', '2.7:0', '2.8:0', '2.9:0',
                    '2.10:0'
                ]
            }
        })

    def test_skipping(self):
        self.getPage('/api/versions/translated/concordance/' +
                     urllib.parse.quote('[{"text": "God"}, {}, {"text": "in"}]') +
                     '/?versions=translated')
        self.assertStatus(200)
        passages = self.json["body"]["passages"]
        self.assertEqual(len(passages), 4)
        self.assertEqual(passages[3], {
            u'section': u'1Co/2/',
            u'phraseid': u'12.15',
            u'wordids': [0],
            u'versions': {
                u'translated': [
                    '12.9:0', '12.10:0', '12.11:0',
                    '12.12:0', '12.13:0', '12.14:0',
                    '12.15:0', '12.16:0', '12.17:0',
                    '12.18:0', '12.19:0', '12.20:0',
                    '12.21:0'
                ]
            }
        })

    def test_parsing_terms(self):
        self.getPage('/api/versions/translated/concordance/' +
                     urllib.parse.quote('[{"text": "in"}, {"case": "D"}]') +
                     '/?versions=translated')
        self.assertStatus(200)
        passages = self.json["body"]["passages"]
        self.assertEqual(len(passages), 31)
        self.assertEqual(passages[0], {
            u'phraseid': u'2.7',
            u'wordids': [0],
            u'section': u'1Co/1/',
            u'versions': {
                u'translated': [
                    '2.1:0',
                    '2.2:0', '2.3:0', '2.4:0', '2.5:0',
                    '2.6:0', '2.7:0', '2.8:0', '2.9:0',
                    '2.10:0', '2.11:0', '2.12:0', '2.13:0'
                ]
            }
        })

    def test_lemma_terms(self):
        self.getPage(
            '/api/versions/translated/concordance/' +
            urllib.parse.quote('[{"lemma": "\u1f10\u03bd"}, {}, '
                         '{"lemma": "\u1f38\u03b7\u03c3\u03bf\u1fe6\u03c2"}]') +
            '/?versions=translated')
        self.assertStatus(200)
        passages = self.json["body"]["passages"]
        self.assertEqual(len(passages), 3)
        self.assertEqual(passages[0], {
            u'phraseid': u'2.7',
            u'wordids': [0],
            u'section': u'1Co/1/',
            u'versions': {
                u'translated': [
                    '2.1:0', '2.2:0', '2.3:0',
                    '2.4:0', '2.5:0',
                    '2.6:0',
                    '2.7:0', '2.8:0', '2.9:0',
                    '2.10:0', '2.11:0', '2.12:0', '2.13:0'
                ]
            }
        })
