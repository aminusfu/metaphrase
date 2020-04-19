"""Metaphrase, a collaborative translation service.

A "work" begins with an original "version", consisting of an ordered
sequence of "text" strings. Each text string in the original is given
a "phrase" ID which is unique within the work. The phrases relate each
text string in any version with the corresponding text in other versions.
The phrase IDs are also used for reference and layout within the UI.
Phrase IDs contain substrings separated by periods in a hierarchy defined
by the work. For example, the Greek New Testament uses the hierarchy of
Book.Chapter.Verse.Word, following the SBLGNT order for numbering the
words within a verse.

A "passage" consists of a sequence of phrase IDs from a work, together
with the corresponding text from one or more versions, ordered by one
of the versions.

The original text is itself one or more versions in this format,
where each item always has a one-to-one correspondence between its
text strings and phrase IDs. This allows multiple "original" versions
of the same work (for example, from different papyri) to vary, from minor
word endings to adding or omitting large passages.

passage = {
    "phrases":  [..., "Foo.3.8.13", "Foo.3.8.13", ...],
    "lemmas":   [...,         5469,         5469, ...],
    "parsing":  [...,          616,          616, ...],
    "versions": {
        "original": [...,       "I am",       "I am", ...],
        "fumanchu": [...,          "I",         "am", ...]
    }
}

Each phrase in the work maps to a lemma and to a parse code. There is no
significance or order to the identifiers in these maps; they exist merely
to match up morphology with phrases.

lemmas = {
    "\u03c0\u03c1\u03bf\u03c3": 5469,
    ...
}

parsing = {
     "V-3AMD-P--": 616,
     ...
}
"""

import os


def abspath(*parts):
    """Return the absolute path after joining the given parts."""
    return os.path.abspath(os.path.join(*parts))


class FileNotFound(Exception):
    pass


def local_path(*parts):
    """Join parts. Raise FileNotFound if the result is outside the first part."""
    path = abspath(*parts)
    if not path.startswith(parts[0]):
        raise FileNotFound()
    return path
