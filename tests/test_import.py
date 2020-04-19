# coding: utf-8
from . import MetaphraseTestCase


p_lille_1_29 = """
ἐὰν δέ τις περὶ ἀδικήματος ἑ[τέ]ρο[υ]
οἰκέτηι ὄντι δίκην γραψάμενος
ὡς ἐλευθέρωι καταδικάσηται
ἐξέστω τῶι κυρίωι ἀναδικῆσαι
ἐν ἡμέραις ε, ἀφʼ ἧς ἂν ἡ εἴσπραξις
γίνηται, καὶ ἂν καταδικασθῆι
ἡ δίκη, τό τε ἐπιδέκατο̣ν ἢ ἐπι-
πεντεκαιδέκατο̣ν ἀποτινέτω
ὁ κύριος, καὶ ἡ πρᾶξις συντελείσθω
κατὰ τοὺς νόμους τοὺς περὶ τῶν
οἰκετῶν ὄντας, πλὴν ὧν τὸ διά-
γραμμα ἀπαγορεύει.
——
μηθενὶ ἐξέστω σώματα πωλεῖν
[ἐπʼ] ἐξαγωγῆι, μηδὲ στίζειν, μη-
δ̣[ὲ]   ̣  ̣[  ̣  ̣]  ̣[  ̣  ̣]  ̣[- ca.13 -]
ἐπιχωρήσηι.
[- ca.14 -]  ̣ι  ̣ δικασ̣τὴς
[1 line missing]
ἐξέστω καὶ τοῖς δούλοις
μαρτυρεῖν.
τῶν δὲ δούλων τῶν μαρτυρησάντων
οἱ δικασταὶ τὴν βάσανον ἐκ τῶν
σωμάτων ποείσθωσαν, παρόντων
τῶν ἀντιδίκων, ἐὰμ μὴ ἐκ τῶν
τεθέντων δικαιωμάτων δύνων-
ται κρίνειν.
——
δούλων ἐπίκλησις καὶ τοῖς καταδικα-
σαμένοις πρᾶξις. ὃς ἂν ἐγκαλῆι
ὑπὸ δούλου ἢ δούλης ἀδικεῖσθαι,
λέγων τὸ ἀδίκημα τῶι κυρίωι
ἐναντίον μὴ ἔλασσον ἢ δύο μαρ-
τύρων, ἀπογραφέσθω πρὸς τοὺς
[νο]μοφύλακας καὶ ἀπαγορευέτω
"""


class TestBasicImport(MetaphraseTestCase):

    def test_populate_section(self):
        # Get the existing lemma counts
        self.getPage('/api/versions/untranslated/lexicon/')
        prev_count = self.json['index']['%CE%BC%CE%AE/']["count"]

        try:
            # Copy the untranslated version to a new one (to DELETE later)
            # Create a new version...
            self.PATCH_json(
                '/api/versions/',
                {"index": {"DDbDP/": {}}}
            )
            self.assertStatus(204)

            # ...and copy the untranslated version to it.
            self.POST_json(
                '/api/versions/DDbDP/', {
                    "element": "shoji:entity",
                    "body": {"parent": "untranslated"}
                }
            )

            # Add a work and section to it.
            self.PATCH_json(
                '/api/versions/DDbDP/', {
                "index": {
                    "p.lille.1/": {"name": "P. Lille 1", "sections": ["29"]}
                }
            })
            self.assertStatus(204)

            # POST the text. We could PUT it, but then we'd have to do all the
            # tokenization and assignation of word ids ourself first. A POST
            # does that for us.
            self.POST_json(
                '/api/versions/DDbDP/text/p.lille.1/29/',
                {"body": {"text": p_lille_1_29}}
            )
            self.assertStatus(204)

            # Assert the changes.
            self.getPage('/api/versions/DDbDP/text/p.lille.1/29/')
            self.assertStatus(200)
            self.assertEqual(
                self.json['order'][:3],
                ["1.1:0", "1.2:0", "1.3:0"]
            )
            self.assertEqual(
                self.get_text(xrange(3)),
                [u'ἐὰν', u'δέ', u'τις']
            )

            # Assert the additions to the lexicon...
            self.assertEqual(
                self.json['index']['1.137'], {
                    u'lemma': u'\u1f41',
                    u'original': u'\u03c4\u1ff6\u03bd',
                    u'parsing': u'T----GPM-',
                    u'text': [u'\u03c4\u1ff6\u03bd']
                }
            )
            self.getPage('/api/versions/DDbDP/lexicon/')
            self.assertStatus(200)
            self.assertEqual(
                self.json['index']['%CE%BC%CE%AE/'],
                {"count": prev_count + 2}
            )
        finally:
            self.getPage('/api/versions/DDbDP/', method="DELETE")
            self.assertStatus(204)
