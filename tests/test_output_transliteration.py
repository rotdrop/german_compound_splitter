import unittest
from unittest import mock

import ahocorasick

from german_compound_splitter import comp_split


def _fake_transliterate(words, loc):
    table = str.maketrans({'ö': 'oe', 'ü': 'ue', 'ä': 'ae', 'ß': 'ss'})
    return [w.translate(table) for w in words]


def _automaton():
    a = ahocorasick.Automaton()
    for w in ['Brötchen', 'Tüte', 'Haus']:
        a.add_word(w.lower(), (True, w, len(w)))
    # transliterated keys as registered by read_dictionary_from_file
    a.add_word('broetchen', (True, 'Brötchen', len('broetchen')))
    a.add_word('tuete', (True, 'Tüte', len('tuete')))
    a.make_automaton()
    return a


class OutputTransliterationTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(comp_split, '_transliterate_words', side_effect=_fake_transliterate)
        self.translit = patcher.start()
        self.addCleanup(patcher.stop)
        self.ahocs = _automaton()

    def test_transliterated_input_gives_transliterated_output(self):
        result = comp_split.dissect('Broetchentuete', self.ahocs, transliteration_locale='de_DE')
        self.assertEqual(result, ['Broetchen', 'Tuete'])
        self.translit.assert_called_once_with(['Brötchen', 'Tüte'], 'de_DE')

    def test_input_with_umlauts_is_not_transliterated(self):
        result = comp_split.dissect('Brötchentüte', self.ahocs, transliteration_locale='de_DE')
        self.assertEqual(result, ['Brötchen', 'Tüte'])
        self.translit.assert_not_called()

    def test_no_locale_keeps_original_forms(self):
        result = comp_split.dissect('Broetchentuete', self.ahocs)
        self.assertEqual(result, ['Brötchen', 'Tüte'])
        self.translit.assert_not_called()

    def test_no_umlaut_in_results_is_not_transliterated(self):
        result = comp_split.dissect('Haushaus', self.ahocs, transliteration_locale='de_DE')
        self.assertEqual(result, ['Haus', 'Haus'])
        self.translit.assert_not_called()


if __name__ == '__main__':
    unittest.main()
