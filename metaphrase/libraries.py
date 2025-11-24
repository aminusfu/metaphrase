from collections import defaultdict
import fcntl
import json
import os
import re
import shutil
import threading
import unicodedata

from metaphrase import abspath, local_path, FileNotFound

# TODO: these are for Greek, and need to be
# 1) moved to a .json file (shared between works), and
# 2) sent via the API instead of duplicated in e.g. section.html.
parsing_category_order = ["part", "person", "tense", "voice",
                          "mood", "case", "number", "gender", "degree"]


def normalize(obj):
    t = type(obj)
    if t is dict:
        return dict((normalize(k), normalize(v)) for k, v in obj.items())
    elif t is list:
        return [normalize(item) for item in obj]
    elif t is str:
        return unicodedata.normalize('NFC', obj)
    else:
        return obj


def indices(list, element):
    """Return all indices where the given element appears in the given list."""
    result = []
    offset = -1
    try:
        while True:
            offset = list.index(element, offset + 1)
            result.append(offset)
    except ValueError:
        return result


def read_json(path):
    """Return deserialized JSON from the given path."""
    if not os.path.exists(path):
        raise FileNotFound(path)

    with open(path, "r") as f:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            data = f.read()
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    return json.loads(data)


def write_json(path, data):
    """Write serialized JSON to the given path."""
    data = json.dumps(data, indent='  ')
    with open(path, "w") as f:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.write(data)
            f.flush()
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


roles = {'none': 0, 'reader': 1, 'writer': 2, 'admin': 3}


class Section:
    """An ordered array of text strings with phrase ids."""

    order = []
    """A list of "phraseid:wordid" strings."""

    entries = {}
    """A dict of (phraseid, attributes) pairs. Each phraseid must be of the
    form: 'verse.phrase'. The attributes must be a dict with keys:
    "parsing", "lemma", "original", and "text".
    """

    indices = {}
    """A dict of (attrname, index) pairs. Each attrname is one of the
    attributes for each entry in self.entries, such as "lemma" or "original".
    Each index is a dict of (attribute-value, [ids]) pairs, where the ids
    are those of each entry who attribute value matches the key.
    """

    def __init__(self, version, workid, sectionid, order=None, entries=None):
        self.version = version
        self.workid = workid
        self.sectionid = sectionid
        self.order = order or []
        self.entries = entries or {}
        self.indices = self.calc_indices()

        self.lock = threading.RLock()

    def add(self, phraseid, text, entry):
        """Append a word to self."""
        e = self.entries.setdefault(id, {"text": []})
        e["text"].append(text)
        e.update(entry)

        self.indices['original'].setdefault(entry['original'], []).append(phraseid)
        self.indices['lemma'].setdefault(entry['lemma'], []).append(phraseid)

        self.order.append("%s:%d" % (phraseid, len(e["text"]) - 1))

    def passage(self, phraseid, context):
        """Return ids (with context) for the given phrase."""
        try:
            minpos = self.order.index("%s:0" % phraseid)
            maxpos = self.order.index("%s:%d" % (phraseid, len(self.entries[phraseid]["text"]) - 1))
        except (KeyError, ValueError):
            return []

        lo = max(minpos - context, 0)
        hi = min(maxpos + context, len(self.order))
        return self.order[lo:hi + 1]

    def find(self, criteria, strict):
        """Return a list of ["verse.phrase", word] ids matching the given criteria.

        Each criterion must be an object; its members define which
        parsing categories to match with the entry for an id.
        For example, {"case": "D"} matches an entry whose charAt(4) == "D".
        The "original" and "lemma" are also legal members. So is "text",
        in which case a text must equal the criterion, unless strict
        is False, in which case the criterion is a regular expression
        which the text must match.

        Values may be:

         * strings, in which case they will be matched exactly. For example:

            {"text": "let", "part": "V", "tense": "A"}

        * lists, in which case each word must match one of the given strings:

            {"text": ["let", "sublet"], "part": "V", "tense": ["A", "P"]}

        * a dict of the form {"not": str or list}:

            {"text": ["let", "sublet"], "part": "V", "tense": {"not": "A"}}
        """
        parsed_criteria = []
        if not isinstance(criteria, list):
            criteria = [criteria]

        for template in criteria:
            if not isinstance(template, dict):
                raise ValueError(
                    "Each criterion MUST be an object, not %s." % repr(template)
                )

            term = {}
            for k, v in template.items():
                inverse = isinstance(v, dict)
                if inverse:
                    v = v["not"]
                if not isinstance(v, list):
                    v = [v]

                term[k] = (inverse, v)

            parsed_criteria.append(term)

        matches = []
        for i, id in enumerate(self.order):
            for j, template in enumerate(parsed_criteria):
                try:
                    phraseid, wordid = self.order[i + j].split(":", 1)
                except IndexError:
                    # Ran out of ids to match.
                    break

                entry = self.entries[phraseid]
                text = entry["text"][int(wordid)]
                if not self.matches_template(entry, text, template, strict):
                    break
            else:
                # We got all the way through all items in the list
                # without breaking, so therefore our text matches.
                matches.append(id)

        return matches

    def matches_template(self, entry, text, template, strict):
        """Return True if the given entry matches the given template.

        The 'template' arg MUST be a dict with zero or more keys from the set
        of parsing categories or "text", "lemma", "original".
        Values MUST be of the form: (inverse, [terms])
        """
        parsing = entry.get('parsing', '')
        for k, v in template.items():
            inverse, terms = v

            match = False
            if k == "text":
                if strict:
                    match = (text in terms)
                else:
                    match = any(re.match(term, text) for term in terms)
            elif k in ("lemma", "original"):
                match = (entry.get(k, None) in terms)
            elif parsing:
                try:
                    charidx = parsing_category_order.index(k)
                    match = (parsing[charidx] in terms)
                except IndexError:
                    return False

            if inverse:
                match = not match
            if not match:
                return False

        return True

    def update(self, entries):
        """Overwrite self.entries with the given entries."""
        with self.lock:
            for phraseid, tup in entries.items():
                e = self.entries[phraseid]
                pretext = len(e["text"])
                e.update(tup)

                # Modify self.order to match
                posttext = len(e["text"])
                if posttext > pretext:
                    # More text than before. Add ids to the order.
                    newids = ["%s:%d" % (phraseid, i) for i in range(pretext, posttext)]
                    if pretext:
                        idxs = [self.order.index("%s:%d" % (phraseid, i))
                                for i in range(pretext)]
                        idxs.sort()
                        last = idxs[-1]
                        self.order[last + 1:last + 1] = newids
                    else:
                        self.order.extend(newids)
                elif posttext < pretext:
                    # Less text than before.
                    for i in range(posttext, pretext):
                        self.order.remove("%s:%d" % (phraseid, i))

    def move_before(self, id, movebefore):
        """Move the word with the given id before the identified word."""
        with self.lock:
            self.order.remove(id)
            newpos = self.order.index(movebefore)
            self.order.insert(newpos, id)

    def calc_indices(self, keys=("original", "lemma")):
        """Calculate indices from entries."""
        indices = {}
        for k in keys:
            idx = {}
            for id, e in self.entries.items():
                idx.setdefault(e[k], []).append(id)
            indices[k] = idx
        return indices

    def matching_entries(self, entry):
        """Return entries whose morphological members match the given entry."""
        matches = []
        for eid in self.indices["original"].get(entry["original"], []):
            e = self.entries[eid]
            if (
                e["parsing"] == entry["parsing"] and
                e["lemma"] == entry["lemma"]
            ):
                matches.append(e)
        return matches

    def translation(self, version):
        """Return new_ids, new_text for self."""
        # For each word, look up the most common text in the target version.
        # We do *not* map ids directly, because we want to:
        # 1) skip any words not present in the source version,
        # 2) preserve the word order in the source version, and
        # 3) fall back to the text in the source version if needed.
        seen = set()
        new_ids, new_text = [], []
        for id in self.order:
            phraseid, wordid = id.split(":", 1)
            if phraseid in seen:
                # We're not going to try to line up multi-word phrases.
                # Just drop the new text in at the first position of the old.
                continue
            seen.add(phraseid)

            # Count the occurence of each word form in the trans_version
            # for the given entry.
            e = self.entries[phraseid]
            best_text = version.translate(e)
            if best_text is None:
                # For now, if no match, default to the text of the source version.
                best_text = [e["text"][int(wordid)]]

            new_ids.extend([(phraseid, i) for i in range(len(best_text))])
            new_text.extend(best_text)

        # TODO: is this really how we want to return this now?
        return new_ids, new_text


class Version:
    """A collection of works (with sections), together with lexical notes."""

    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.works_path = os.path.join(path, 'works')

        try:
            self.version_notes = read_json(local_path(path, "version_notes.json"))
        except FileNotFound:
            self.version_notes = ""

        try:
            self.lexical_notes = read_json(local_path(path, "lexical_notes.json"))
        except FileNotFound:
            self.lexical_notes = {}

        try:
            cat = read_json(local_path(self.works_path, "catalog.json"))
            self.works = cat["index"]
            self.worksorder = cat["order"]
        except FileNotFound:
            self.works = {}
            self.worksorder = []

        self.section_cache = {}

    def destroy_work(self, workid):
        """Destroy directories for this Work."""
        self.works.pop(workid, None)
        if workid in self.worksorder:
            self.worksorder.remove(workid)
        path = local_path(self.works_path, workid)
        if os.path.exists(path):
            shutil.rmtree(path)

    def save_works(self):
        """Store the ordered list of works for this version.

        Each work is a dict of the form {"id", "name", "sections": [...]}
        """
        works_path = local_path(self.works_path)
        if not os.path.exists(works_path):
            os.makedirs(works_path)

        path = local_path(self.works_path, "catalog.json")
        write_json(path, {"order": self.worksorder, "index": self.works})

    def load_section(self, workid, sectionid):
        """Return this version of the identified section."""
        key = (workid, sectionid)
        if key in self.section_cache:
            return self.section_cache[key]
        else:
            data = read_json(local_path(self.works_path, workid, sectionid + ".json"))

            # Migrate
            needs_save = False
            if "text" in data:
                seen = {}
                order = []
                for id in data["ids"]:
                    newid = ".".join(id.split(".")[-2:])
                    if newid not in seen:
                        seen[newid] = 0
                    else:
                        seen[newid] += 1
                    order.append([newid, seen[newid]])

                oldentries = read_json(local_path(self.works_path, workid, sectionid + ".lex"))["entries"]
                entries = {}
                for id, entry in oldentries.items():
                    entry.pop("id")
                    newid = ".".join(id.split(".")[-2:])
                    entries[newid] = entry
                    entry["text"] = [data["text"][i] for i in indices(data["ids"], id)]

                data = {"order": order, "entries": entries}
                needs_save = True

            if data["order"] and isinstance(data["order"][0], list):
                data["order"] = ["%s:%d" % (phraseid, wordid)
                                 for phraseid, wordid in data["order"]]
                needs_save = True

            if data["entries"] and "part" in next(iter(data["entries"].values())):
                partmap = {
                    "A-": "A",
                    "C-": "C",
                    "D-": "D",
                    "I-": "I",
                    "N-": "N",
                    "P-": "P",
                    "RA": "T",
                    "RD": "d",
                    "RI": "Q",
                    "RP": "p",
                    "RR": "r",
                    "V-": "V",
                    "X-": "X",
                    "S-": "S",
                    "--": "-"
                }
                for e in data["entries"].values():
                    part = e.pop("part", "--")
                    e["parsing"] = partmap[part] + e["parsing"]
                needs_save = True

            section = Section(self.name, workid, sectionid, **data)
            self.section_cache[key] = section

            if needs_save:
                self.save_section(section)

            return section

    def save_section(self, section):
        """Store the given section."""
        key = (section.workid, section.sectionid)
        self.section_cache[key] = section

        path = local_path(self.works_path, section.workid, section.sectionid + ".json")
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))

        data = {
            "order": section.order,
            "entries": section.entries
        }
        write_json(path, data)

        try:
            work = self.works[section.workid]
            if section.sectionid not in work["sections"]:
                work["sections"].append(section.sectionid)
                self.save_works()
        except KeyError:
            self.works[section.workid] = {
                "name": section.workid,
                "sections": [section.sectionid]
            }
            self.worksorder.append(section.workid)
            self.save_works()

    def word_counts(self):
        """Return a dict of all {word: count} pairs from the version."""
        words = {}
        for workid, work in self.works.items():
            for sectionid in work["sections"]:
                section = self.load_section(workid, sectionid)
                for e in section.entries.values():
                    for text in e["text"]:
                        if text in words:
                            words[text] += 1
                        else:
                            words[text] = 1
        return words

    def save_version_notes(self):
        """Store the version notes for this version."""
        path = local_path(self.path, "version_notes.json")
        write_json(path, self.version_notes)

    def save_lexical_notes(self):
        """Store the lexical notes for this version."""
        path = local_path(self.path, "lexical_notes.json")
        write_json(path, self.lexical_notes)

    def lemma_counts(self):
        """Return a dict of all {lemma: count} pairs from the lexicons."""
        lemmas = {}
        for workid, work in self.works.items():
            for sectionid in work["sections"]:
                lex = self.load_section(workid, sectionid)
                for lemma, ids in lex.indices.get("lemma", {}).items():
                    if lemma in lemmas:
                        lemmas[lemma] += len(ids)
                    else:
                        lemmas[lemma] = len(ids)
        return lemmas

    def morphology_map(self):
        """Return the most-common {original: entry} pairs from this version."""
        m = {}
        for workid, work in self.works.items():
            for sectionid in work["sections"]:
                try:
                    section = self.load_section(workid, sectionid)
                except FileNotFound:
                    continue

                for entry in section.entries.values():
                    orig = entry["original"]
                    if orig not in m:
                        m[orig] = {}

                    key = (entry['lemma'], entry['parsing'])
                    if key not in m[orig]:
                        m[orig][key] = 1
                    else:
                        m[orig][key] += 1

        # Grab the most popular
        sorted_m = dict(
            (orig, sorted([(c, k) for k, c in keycounts.items()])[-1][1])
            for orig, keycounts in m.items()
        )

        return dict(
            (orig, {"lemma": e[0], "parsing": e[1], "original": orig})
            for orig, e in sorted_m.items()
        )

    def translate(self, entry):
        """Return the most-common text from this version for the given entry."""
        match_counts = defaultdict(int)
        for workid, work in self.works.items():
            for sid in work["sections"]:
                try:
                    vsect = self.load_section(workid, sid)
                except FileNotFound:
                    continue

                for m in vsect.matching_entries(entry):
                    t = tuple(vsect.index[m["id"]])
                    match_counts[t] += 1

        if match_counts:
            match_counts = [(c, k) for k, c in match_counts.items()]
            return sorted(match_counts)[-1][1]

        return None


class Versions:

    def __init__(self, path, auth):
        self.path = path
        self.auth = auth

        self.version_names = []
        for fname in sorted(os.listdir(path)):
            if os.path.isdir(abspath(path, fname)):
                self.version_names.append(fname)
        self.version_cache = {}

    def copy_sections(self, from_version, to_version, worksections=None, translate=False):
        """Copy sections of works form one version to another.

        If worksections is None (the default), all sections from all works
        will be copied. If a dict of works, only those sections will be copied.
        """
        if worksections is None:
            worksections = from_version.works

        # Iterate using the order of the fromversion so new works
        # get added in the same order.
        for workid in from_version.worksorder:
            newwork = worksections.get(workid, None)
            if newwork is None:
                continue

            if workid not in to_version.works:
                name = newwork.get("name", from_version.works[workid]["name"])
                to_version.works[workid] = {"name": name, "sections": []}
                to_version.worksorder.append(workid)
            sections = to_version.works[workid]["sections"]

            for sectionid in newwork["sections"]:
                src = os.path.join(from_version.works_path, workid)
                dst = os.path.join(to_version.works_path, workid)
                if not os.path.exists(dst):
                    os.makedirs(dst)

                # These will overwrite any existing file
                shutil.copyfile(
                    "%s/%s.json" % (src, sectionid),
                    "%s/%s.json" % (dst, sectionid)
                )

                if sectionid not in sections:
                    sections.append(sectionid)
                to_version.section_cache.pop((workid, sectionid), None)

                if translate:
                    section = to_version.load_section(workid, sectionid)
                    new_ids, new_text = section.translate(to_version)
                    section.order = new_ids
                    section.text = new_text
                    to_version.save_section(section)

        to_version.save_works()

    def __getitem__(self, name):
        if name in self.version_cache:
            return self.version_cache[name]
        else:
            version = Version(name, local_path(self.path, name))
            self.version_cache[name] = version
            return version

    def destroy_version(self, version):
        self.version_names.remove(version.name)
        self.version_cache.pop(version.name)
        self.auth.pop(version.name, None)
        shutil.rmtree(version.path, ignore_errors=True)

    def items(self):
        for k in self.version_names:
            yield k, self[k]

    def permit(self, version, user, role):
        """Return True if the user (or public) has at least the given role."""
        byuser = self.auth.get(version, {}).get("permissions", {})
        my_role = byuser.get(user, 'none')
        public_role = byuser.get('public', 'none')

        role_value = roles.get(role, 0)
        permitted = (
            role_value <= roles.get(my_role, 0) or
            role_value <= roles.get(public_role, 0)
        )
        return permitted


class Library:

    def __init__(self, path):
        self.path = path
        self.auth = self.load_auth()
        self.versions = Versions(local_path(path, "versions"), self.auth["versions"])

        # TODO: move into each version (as part of the lexicon, probably)
        self.refs = normalize(self.load_refs())
        self.inverse_refs = {}
        for child, parents in self.refs.items():
            for p in parents:
                children = self.inverse_refs.setdefault(p, [])
                children.append(child)

    @classmethod
    def create(cls, path):
        """Create directories for a new Library at the given path."""
        if not os.path.exists(path):
            os.makedirs(path)
            os.makedirs(local_path(path, "versions"))
            write_json(local_path(path, "auth.json"), {"versions": {}})
        return cls(path)

    def load_auth(self):
        """Load the auth data from disk."""
        try:
            return read_json(local_path(self.path, "auth.json"))
        except FileNotFound:
            return {}

    def save_auth(self):
        """Save the auth data to disk."""
        path = local_path(self.path, "auth.json")
        write_json(path, self.auth)

    def load_refs(self):
        """Load a flat map of {child: [parents]} pairs."""
        path = local_path(self.path, "refs.json")
        try:
            data = read_json(path)
        except FileNotFound:
            data = {}
        return data

    def save_refs(self):
        """Save a flat map of {child: [parents]} pairs."""
        path = local_path(self.path, "refs.json")
        write_json(path, self.refs)

    def _add_passages(self, workid, sectionid, versions, ids, context):
        """Return entries, passages with data from the given section."""
        # Make a single passage for all words in the passage.
        passages = []
        index = {}
        for id in ids:
            phraseid, wordid = id.split(":", 1)
            p = index.get(phraseid, None)
            if p is None:
                index[phraseid] = p = {
                    "section": workid + "/" + sectionid + "/",
                    "phraseid": phraseid,
                    "wordids": [],
                    # We will fill this below with one passage per version.
                    "versions": {}
                }
                passages.append(p)
            p["wordids"].append(int(wordid))

        entries = {}
        for version in versions:
            entries[version] = {}

            v = self.versions[version]
            try:
                section = v.load_section(workid, sectionid)
            except FileNotFound:
                continue

            for p in passages:
                # For each phrase (and its surrounding text)...
                surrounding = section.passage(p["phraseid"], context)

                # ...add passage ids.
                p["versions"][version] = surrounding

                # ...add lexicon entries
                v_entries = entries[version]
                for id in surrounding:
                    phraseid, wordid = id.split(":", 1)
                    e = section.entries[phraseid]
                    v_entries["/".join((workid, sectionid, phraseid))] = e

        return entries, passages

    MAX_FIND_RESULT = 250 * (6 + 1) * 2 * 3

    def concordance(self, versions, criteria, in_version, strict=False, context=6):
        """Return (entries, passages, complete) which contain the given word(s).

        If strict is True, the text of each entry must equal the given criteria;
        otherwise, each criterion is used as a regular expression with re.match.

        The 'complete' return value is True if all occurrences are included in
        the result. If False, we exceeded the system limit, which is mostly
        to keep memory usage down on a free host for now.
        """
        # context + 1 for the word itself (which likely averages to 2 anyway)
        # and to never have a 0 term.
        mult = (context + 1) * 2 * len(versions)
        approx_words = 0

        entries = dict((v, {}) for v in versions)
        passages = []

        base_version = self.versions[in_version]
        for workid in base_version.worksorder:
            work = base_version.works[workid]
            for sectionid in work["sections"]:
                # Load the text for this section and find matches.
                try:
                    section = base_version.load_section(workid, sectionid)
                except FileNotFound:
                    continue

                matching_ids = section.find(criteria, strict)
                if matching_ids:
                    new_entries, new_passages = self._add_passages(
                        workid, sectionid, versions, matching_ids, context)
                    for version, e in new_entries.items():
                        entries[version].update(e)
                    passages.extend(new_passages)
                    approx_words += len(new_passages) * mult
                    if approx_words > self.MAX_FIND_RESULT:
                        return entries, passages, False

        return entries, passages, True

    def family(self, lemma):
        r"""Return a tree of ancestors and descendants for the given lemma.

        Each node in the tree is a dict with a lemma member, plus an
        optional parents and/or children members.

        Example:

          ana              > sunanabaino
              \           /
               > anabaino
              /           \
        baino              > prosanabaino

        {
            "lemma": "anabaino",
            "parents": [
                {"lemma": "ana", "parents": []},
                {"lemma": "baino", "parents": []}
            ]
            children: [
                {"lemma": "sunanabaino", "children": []},
                {"lemma": "prosanabaino", "children": []}
            ]
        }
        """
        lemma = normalize(lemma)
        return {
            "lemma": lemma,
            "parents": self.parents(lemma, set()),
            "children": self.children(lemma, set())
        }

    def parents(self, lemma, seen):
        if lemma in seen or lemma not in self.refs:
            return

        ps = self.refs[lemma]
        seen |= set(ps)
        return [{"lemma": p, "parents": self.parents(p, seen)}
                for p in ps]

    def children(self, lemma, seen):
        if lemma in seen or lemma not in self.inverse_refs:
            return

        ch = self.inverse_refs[lemma]
        seen |= set(ch)
        return [{"lemma": c, "children": self.children(c, seen)}
                for c in ch]
