import os
import sys

from metaphrase import local_path
from metaphrase.libraries import Book, Lexicon, Work


class MorphSBLGNT:
    """A transformer from MorphGNT (based on SBLGNT) files to Metaphrase."""

    # THE SBLGNT includes brackets in some text strings.
    # We use the "bare" string so we don't need to strip these at the moment.
    markers = (u"\u2e00", u"\u2e01", u"\u2e02", u"\u2e03")

    punctuation = (u",", u";", u".", u"\u00B7")

    books = [
        {"id": "Mt", "name": "Matthew"},
        {"id": "Mk", "name": "Mark"},
        {"id": "Lk", "name": "Luke"},
        {"id": "Jn", "name": "John"},
        {"id": "Ac", "name": "Acts"},
        {"id": "Ro", "name": "Romans"},
        {"id": "1Co", "name": "1 Corinthians"},
        {"id": "2Co", "name": "2 Corinthians"},
        {"id": "Ga", "name": "Galatians"},
        {"id": "Eph", "name": "Ephesians"},
        {"id": "Php", "name": "Philippians"},
        {"id": "Col", "name": "Colossians"},
        {"id": "1Th", "name": "1 Thessalonians"},
        {"id": "2Th", "name": "2 Thessalonians"},
        {"id": "1Ti", "name": "1 Timothy"},
        {"id": "2Ti", "name": "2 Timothy"},
        {"id": "Tit", "name": "Titus"},
        {"id": "Phm", "name": "Philemon"},
        {"id": "Heb", "name": "Hebrews"},
        {"id": "Jas", "name": "James"},
        {"id": "1Pe", "name": "1 Peter"},
        {"id": "2Pe", "name": "2 Peter"},
        {"id": "1Jn", "name": "1 John"},
        {"id": "2Jn", "name": "2 John"},
        {"id": "3Jn", "name": "3 John"},
        {"id": "Jud", "name": "Jude"},
        {"id": "Re", "name": "Revelation"},
    ]

    def __init__(self, path):
        self.path = path
        self._filenames = {}
        for fname in sorted(os.listdir(path)):
            if fname.endswith(".txt"):
                try:
                    number, bookid, etc = fname.split("-", 2)
                except ValueError:
                    continue
                else:
                    self._filenames[bookid] = fname

    def load_lexicon_and_book(self, bookid):
        """Return the Lexicon and Book of the given id."""
        lex = Lexicon(bookid)
        book = Book(bookid)

        fname = self._filenames[bookid]
        path = local_path(self.path, fname)
        with open(path, 'rb') as f:
            last_bcv = None
            bcv_suffix = 1
            for line in f.read().splitlines():
                cols = line.decode('utf-8').split(" ")
                bcv, part, parsing, text, bare, norm, lemma = cols
                booknumber, chapter, verse = map(int, (bcv[:2], bcv[2:4], bcv[4:6]))

                # The SBLGNT starts with a book/chapter/verse number.
                # We want unique ids per word in the source so that
                # we can match translations to them.
                bcv = "%s.%s.%s" % (bookid, chapter, verse)
                if bcv == last_bcv:
                    bcv_suffix += 1
                else:
                    bcv_suffix = 1
                id = "%s.%s" % (bcv, bcv_suffix)
                last_bcv = bcv

                lex.add({
                    "id": id,
                    "original": bare,
                    "part": part,
                    "parsing": parsing,
                    "lemma": lemma
                })
                book.add(bare, id)

                # The SBLGNT includes punctuation in the text itself.
                # Add Punctuation instances for these.
                for p in self.punctuation:
                    if p in text:
                        bcv_suffix += 1
                        id = "%s.%s" % (bcv, bcv_suffix)

                        lex.add({
                            "id": id,
                            "original": p,
                            "part": "S-",
                            "parsing": '',
                            "lemma": p
                        })
                        book.add(p, id)

        return lex, book


if __name__ == '__main__':
    try:
        src = os.path.abspath(sys.argv[1])
        dst = os.path.abspath(sys.argv[2])
    except IndexError:
        print """
Usage: morphsblgnt.py source destination

    source: The file path to the MorphGNT files.
    destination: The file path for a new Metaphrase Work based on the given src.
"""
        sys.exit(1)

    mgnt = MorphSBLGNT(src)
    work = Work(dst)
    work.books = mgnt.books
    work.save_books()

    untrans = work.translations["sblgnt"]
    for book in mgnt.books:
        print "Converting", book["name"]
        lex, book = mgnt.load_lexicon_and_book(book["id"])
        work.lexicons.save(lex)
        untrans.save(book)
