import unittest
from unittest import mock
from types import SimpleNamespace

import ahocorasick

from german_compound_splitter import comp_split


def _automaton(*words):
    automaton = ahocorasick.Automaton()
    for word in words:
        automaton.add_word(word.lower(), (word[0].isupper(), word, len(word)))
    automaton.make_automaton()
    return automaton


class TransliterationTests(unittest.TestCase):
    def test_nonzero_exit_status_with_valid_output_is_accepted(self):
        result = SimpleNamespace(stdout='ae', stderr='warning', returncode=1)
        with mock.patch.object(comp_split.subprocess, 'run', return_value=result) as run:
            self.assertEqual(comp_split._transliterate_words(['ä'], 'de_DE'), ['ae'])
            comp_split._validate_iconv_locales(['de_DE'])
        self.assertTrue(all('check' not in call.kwargs for call in run.call_args_list))

    def test_transliteration_reports_iconv_errors(self):
        with mock.patch.object(
                comp_split.subprocess, 'run',
                return_value=SimpleNamespace(stdout='', stderr='conversion failed', returncode=1)):
            with self.assertRaisesRegex(RuntimeError, 'conversion failed'):
                comp_split._transliterate_words(['ä'], 'de_DE')

    def test_iconv_locale_validation_rejects_empty_or_untransliterated_output(self):
        for output in ('', '?'):
            with self.subTest(output=output), mock.patch.object(
                    comp_split.subprocess, 'run',
                    return_value=SimpleNamespace(stdout=output, stderr='', returncode=0)):
                with self.assertRaisesRegex(ValueError, 'does not support iconv transliteration'):
                    comp_split._validate_iconv_locales(['de_DE'])

    def test_transliteration_rejects_unexpected_line_count(self):
        with mock.patch.object(
                comp_split.subprocess, 'run',
                return_value=SimpleNamespace(stdout='', stderr='')):
            with self.assertRaisesRegex(RuntimeError, 'unexpected number'):
                comp_split._transliterate_words(['ä'], 'de_DE')

    def test_iconv_probe_propagates_command_failure(self):
        with mock.patch.object(comp_split.subprocess, 'run', side_effect=OSError('iconv missing')):
            with self.assertRaisesRegex(OSError, 'iconv missing'):
                comp_split._validate_iconv_locales(['de_DE'])


class DictionaryTests(unittest.TestCase):
    def test_read_dictionary_skips_blank_lines_and_preserves_dictionary_entries(self):
        with mock.patch.object(comp_split, '_validate_locales'), \
                mock.patch.object(comp_split, '_validate_iconv_locales'), \
                mock.patch.object(comp_split, '_transliterate_words', return_value=['haus', 'haeus']):
            import os
            import tempfile
            with tempfile.TemporaryDirectory() as directory:
                path = os.path.join(directory, 'dict.txt')
                with open(path, 'w', encoding='utf8') as dictionary:
                    dictionary.write('Haus\n\nHäus\n')
                automaton = comp_split.read_dictionary_from_file(
                    path, transliteration_locales='de_DE')

        self.assertIn('haus', automaton)
        self.assertEqual(automaton.get('haus'), (True, 'Haus', 4))
        self.assertEqual(automaton.get('haeus'), (True, 'Häus', 5))


class HelpersTests(unittest.TestCase):
    def test_abbreviation_detection(self):
        self.assertTrue(comp_split._is_abbreviation((True, 'ARD', 3)))
        self.assertTrue(comp_split._is_abbreviation((False, 'mA', 2)))
        self.assertTrue(comp_split._is_abbreviation((True, 'Mi', 2)))
        self.assertFalse(comp_split._is_abbreviation((True, 'Haus', 4)))

    def test_check_if_suffix(self):
        self.assertEqual(comp_split._check_if_suffix('enHaus'), 'en')
        self.assertIsNone(comp_split._check_if_suffix('xyz'))

    def test_merge_fractions(self):
        self.assertEqual(comp_split.merge_fractions([]), [])
        self.assertEqual(comp_split.merge_fractions(['Haus', 'ung']), ['Hausung'])
        self.assertEqual(comp_split.merge_fractions(['ab', 'Haus']), ['abHaus'])
        self.assertEqual(comp_split.merge_fractions(['Haus', 'Boot', 'Haus']),
                         ['Haus', 'Boot', 'Haus'])
        self.assertEqual(comp_split.merge_fractions(['Haus', 'ung', 'Boot']),
                         ['Hausung', 'Boot'])

    def test_compute_singular_uses_dictionary_then_umlaut_fallback(self):
        automaton = _automaton('Haus', 'Maus')
        self.assertEqual(comp_split.compute_singular('Häuser', automaton), 'Haus')
        self.assertEqual(comp_split.compute_singular('Mäuse', automaton), 'Maus')
        self.assertEqual(comp_split.compute_singular('Boot', automaton), 'Boot')


class DissectTests(unittest.TestCase):
    def test_no_match_and_abbreviation_are_returned_unchanged(self):
        self.assertEqual(comp_split.dissect('Fremdwort', _automaton('Haus')), ['Fremdwort'])
        self.assertEqual(comp_split.dissect('ARD', _automaton('ARD'), only_nouns=False), ['ARD'])

    def test_lowercase_entries_are_only_included_when_requested(self):
        automaton = _automaton('Haus', 'und', 'Boot')
        self.assertEqual(comp_split.dissect('HausundBoot', automaton, only_nouns=False),
                         ['Haus', 'und', 'Boot'])

    def test_plural_link_and_singular_option(self):
        self.assertEqual(comp_split.dissect('HundeHaus', _automaton('Hund', 'Haus')),
                         ['Hund', 'Haus'])
        self.assertEqual(comp_split.dissect(
            'HundeHaus', _automaton('Hund', 'Hunde', 'Haus'), make_singular=True),
            ['Hund', 'Haus'])

    def test_explicit_transliteration_is_used_for_output(self):
        automaton = ahocorasick.Automaton()
        automaton.add_word('broetchen', (True, 'Brötchen', 9))
        automaton.make_automaton()
        with mock.patch.object(comp_split, '_transliterate_words', return_value=['Broetchen']) as transliterate:
            result = comp_split.dissect('Broetchen', automaton, transliteration_locale='de_DE')

        self.assertEqual(result, ['Broetchen'])
        transliterate.assert_called_once_with(['Brötchen'], 'de_DE')


if __name__ == '__main__':
    unittest.main()
