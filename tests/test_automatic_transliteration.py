import unittest
from unittest import mock

import ahocorasick

from german_compound_splitter import comp_split
from german_compound_splitter.comp_split import TransliteratingAutomaton

TABLES = {
    'de_DE': str.maketrans({'ö': 'oe', 'ü': 'ue', 'ä': 'ae', 'ß': 'ss'}),
    'sv_SE': str.maketrans({'ö': 'o', 'ü': 'u', 'ä': 'a', 'ß': 'ss'}),
}


def _fake_transliterate(words, loc):
    return [w.translate(TABLES[loc]) for w in words]


def _automaton(locales):
    a = ahocorasick.Automaton()
    for w in ['Brötchen', 'Tüte', 'Haus']:
        a.add_word(w.lower(), (True, w, len(w)))
    for loc in locales:
        for w in ['Brötchen', 'Tüte']:
            t = w.lower().translate(TABLES[loc])
            if t not in a:
                a.add_word(t, (True, w, len(t)))
    a.make_automaton()
    return TransliteratingAutomaton(a, locales)


class WrapperTests(unittest.TestCase):
    def test_delegation(self):
        w = _automaton(['de_DE'])
        self.assertEqual(w.locales, ['de_DE'])
        self.assertIn('haus', w)
        self.assertTrue(w.exists('tuete'))
        self.assertEqual(w.get('haus')[1], 'Haus')
        self.assertEqual(len(w), len(w.automaton))

    def test_no_locales(self):
        self.assertIsNone(TransliteratingAutomaton(ahocorasick.Automaton()).detect_locale('x', ['y']))

    def test_read_dictionary_returns_wrapper(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'dict.txt')
            with open(path, 'w', encoding='utf8') as f:
                f.write('Haus\nTüte\n')
            with mock.patch.object(comp_split, '_validate_locales'), \
                    mock.patch.object(comp_split, '_validate_iconv_locales'), \
                    mock.patch.object(comp_split, '_transliterate_words', side_effect=_fake_transliterate):
                w = comp_split.read_dictionary_from_file(path, transliteration_locales='de_DE')
                self.assertEqual(w.locales, ['de_DE'])
                self.assertIn('tuete', w)
                w = comp_split.read_dictionary_from_file(path)
                self.assertEqual(w.locales, [])


class AutomaticOutputTests(unittest.TestCase):
    def setUp(self):
        p = mock.patch.object(comp_split, '_transliterate_words', side_effect=_fake_transliterate)
        self.translit = p.start()
        self.addCleanup(p.stop)

    def test_single_locale_is_used(self):
        result = comp_split.dissect('Broetchentuete', _automaton(['de_DE']))
        self.assertEqual(result, ['Broetchen', 'Tuete'])

    def test_multiple_locales_detects_best(self):
        ahocs = _automaton(['sv_SE', 'de_DE'])
        self.assertEqual(comp_split.dissect('Broetchentuete', ahocs), ['Broetchen', 'Tuete'])
        self.assertEqual(comp_split.dissect('Brotchentute', ahocs), ['Brotchen', 'Tute'])

    def test_detection_with_merged_artifacts(self):
        # words do not concatenate to the compound, but sub-words still discriminate the locales
        ahocs = _automaton(['sv_SE', 'de_DE'])
        self.assertEqual(ahocs.detect_locale('xbroetchenyy', ['Brötchen', 'Tüte']), 'de_DE')
        self.assertEqual(ahocs.detect_locale('xbrotchenyy', ['Brötchen', 'Tüte']), 'sv_SE')

    def test_umlaut_words_must_be_found_in_order(self):
        ahocs = _automaton(['sv_SE', 'de_DE'])
        self.assertEqual(ahocs.detect_locale('baerbarbar', ['Bär', 'Bar', 'Bar']), 'de_DE')
        self.assertEqual(ahocs.detect_locale('barbaerbar', ['Bär', 'Bar', 'Bar']), 'de_DE')
        self.assertEqual(ahocs.detect_locale('barbarbar', ['Bär', 'Bar', 'Bar']), 'sv_SE')

    def test_detection_falls_back_to_similarity(self):
        ahocs = _automaton(['sv_SE', 'de_DE'])
        self.assertEqual(ahocs.detect_locale('broetchn', ['Brötchen']), 'de_DE')

    def test_detection_tie_prefers_first(self):
        ahocs = _automaton(['sv_SE', 'de_DE'])
        self.assertEqual(ahocs.detect_locale('haus', ['Haus']), 'sv_SE')

    def test_explicit_locale_overrides(self):
        ahocs = _automaton(['de_DE', 'sv_SE'])
        self.assertEqual(comp_split.dissect('Broetchentuete', ahocs, transliteration_locale='sv_SE'),
                         ['Brotchen', 'Tute'])

    def test_umlaut_input_untouched(self):
        self.assertEqual(comp_split.dissect('Brötchentüte', _automaton(['de_DE'])), ['Brötchen', 'Tüte'])

    def test_no_locales_no_transliteration(self):
        ahocs = _automaton(['de_DE'])
        ahocs.locales = []
        self.assertEqual(comp_split.dissect('Broetchentuete', ahocs), ['Brötchen', 'Tüte'])


if __name__ == '__main__':
    unittest.main()
