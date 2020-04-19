# coding: utf-8

from . import MetaphraseTestCase


class TestLexicalNotes(MetaphraseTestCase):

    def test_notes(self):
        self.getPage('/api/versions/translated/notes/')
        self.assertStatus(200)
        self.assertJSON({
            "self": "http://local.metaphrase.org:8080/api/versions/translated/notes/",
            "element": "shoji:catalog",
            "catalogs": {
                "lexical": "http://local.metaphrase.org:8080/api/versions/translated/notes/lexical/"
            }
        })

    def test_notes_lexical(self):
        self.getPage('/api/versions/translated/notes/lexical/')
        self.assertStatus(200)
        self.assertJSON({
            "self": "http://local.metaphrase.org:8080/api/versions/translated/notes/lexical/",
            "element": "shoji:catalog",
            "description": "A collection of notes for each lemma. GET a Note by lemma, PUT a Note to create or replace, or DELETE.",
            "index": {}
        })

    def test_no_lexical_note(self):
        self.getPage('/api/versions/translated/notes/lexical/foo/')
        self.assertStatus(404)

    def test_put_get_delete(self):
        # Add a note
        lemma = '%ce%ba%ce%bb%ce%b7%cf%84%cf%8c%cf%82'
        url = '/api/versions/translated/notes/lexical/' + lemma + "/"
        note = "TDNT: 'called', 'named', 'invited'"
        self.PUT_json(url, {"body": {"note": note}})
        self.assertStatus(204)

        # Assert the changes.
        self.getPage(url)
        self.assertStatus(200)
        self.assertEqual(self.json['body']['note'], note)

        # Update the note.
        self.PUT_json(url, {"body": {"note": note + "."}})
        self.assertStatus(204)

        # Assert the changes.
        self.getPage(url)
        self.assertStatus(200)
        self.assertEqual(self.json['body']['note'], note + ".")

        # Delete the note.
        self.getPage(url, method="DELETE")
        self.assertStatus(204)

        # Assert the deletion.
        self.getPage(url)
        self.assertStatus(404)
