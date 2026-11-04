"""Fail-closed one-line d4 Main.cpp precision-variant patch contract."""
from unittest import TestCase
from precision_variant import MARKER, OLD, patch_source


class SourceMutationContract(TestCase):
    def test_only_anchor_is_modified(self):
        original = '#include <gmp.h>\n' + OLD + '\n  return 0;\n'
        result = patch_source(original)
        self.assertEqual(result.count(MARKER), 1)
        self.assertEqual(result.count('mpf_set_default_prec(426);'), 1)
        self.assertEqual(result.split('  auto start')[1],
                         original.split('  auto start')[1])
        with self.assertRaisesRegex(ValueError, 'already patched'):
            patch_source(result)

    def test_unknown_upstream_fails_closed(self):
        with self.assertRaisesRegex(ValueError, 'unrecognized'):
            patch_source('int main() { return 0; }')
