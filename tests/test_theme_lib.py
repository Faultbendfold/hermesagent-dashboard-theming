#!/usr/bin/env python3
"""Unit tests for theme_lib -- the maths and the YAML subset reader.

    python3 -m unittest discover -s tests -v      (from the repository root)
    ./tools/verify.sh                             (runs them as part of the suite)
"""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skills", "hermes-dashboard-theming", "scripts"))

import theme_lib as t  # noqa: E402


class ContrastMath(unittest.TestCase):
    def test_luminance_bounds(self):
        self.assertAlmostEqual(t.lum("#000000"), 0.0, places=6)
        self.assertAlmostEqual(t.lum("#FFFFFF"), 1.0, places=6)

    def test_ratio_extremes(self):
        self.assertAlmostEqual(t.ratio("#000000", "#FFFFFF"), 21.0, places=2)
        self.assertAlmostEqual(t.ratio("#123456", "#123456"), 1.0, places=6)

    def test_ratio_is_symmetric(self):
        self.assertAlmostEqual(t.ratio("#1F2937", "#F8F9FB"), t.ratio("#F8F9FB", "#1F2937"))

    def test_mix_endpoints(self):
        self.assertEqual(t.mix("#000000", "#FFFFFF", 0.0), "#000000")
        self.assertEqual(t.mix("#000000", "#FFFFFF", 1.0), "#FFFFFF")

    def test_norm_hex_short_form(self):
        self.assertEqual(t.norm_hex("#abc"), "#AABBCC")
        self.assertTrue(t.is_hex("#AABBCC"))
        self.assertFalse(t.is_hex("rgb(1,2,3)"))

    def test_lighten_darken_reach_their_target(self):
        up = t.lighten_to("#123456", 0.6)
        down = t.darken_to("#123456", 0.02)
        self.assertGreaterEqual(t.lum(up), 0.6)
        self.assertLessEqual(t.lum(down), 0.02)


class Fit(unittest.TestCase):
    """fit() regressed once: a colour that already met the target was pushed
    past it, all the way to `toward`."""

    def test_already_passing_colour_is_returned_unchanged(self):
        self.assertEqual(t.fit("#15803D", "#FFFFFF", 4.5, "#FFFFFF"), "#15803D")
        self.assertEqual(t.fit("#111827", "#F8F9FB", 7.0, "#000000"), "#111827")

    def test_reaches_the_target_when_it_has_to(self):
        out = t.fit("#9AA0A6", "#FFFFFF", 4.5, "#000000")
        self.assertGreaterEqual(t.ratio(out, "#FFFFFF"), 4.5)


class YamlSubset(unittest.TestCase):
    def test_nested_maps_scalars_and_block(self):
        doc = t.parse_yaml(
            "name: demo\n"
            "label: \"Demo\"   # trailing comment\n"
            "palette:\n"
            "  background: \"#F8F9FB\"\n"
            "  noiseOpacity: 0\n"
            "  foreground:\n"
            "    hex: \"#FFFFFF\"\n"
            "    alpha: 0\n"
            "layout:\n"
            "  density: comfortable\n"
            "customCSS: |\n"
            "  :root { --x: 1; }\n"
            "  .a { color: #FFF; }\n"
        )
        self.assertEqual(doc["label"], "Demo")
        self.assertEqual(doc["palette"]["background"], "#F8F9FB")
        self.assertEqual(doc["palette"]["foreground"]["hex"], "#FFFFFF")
        self.assertEqual(doc["layout"]["density"], "comfortable")
        self.assertIn("--x: 1;", doc["customCSS"])
        self.assertTrue(doc["customCSS"].endswith("\n"))

    def test_single_quotes_and_escaped_quote(self):
        doc = t.parse_yaml("a: 'it''s'\nb: 'plain'\n")
        self.assertEqual(doc["a"], "it's")
        self.assertEqual(doc["b"], "plain")

    def test_sequences_are_refused_loudly(self):
        with self.assertRaises(t.YamlError):
            t.parse_yaml("list:\n  - one\n")

    def test_unterminated_quote_is_an_error(self):
        with self.assertRaises(t.YamlError):
            t.parse_yaml("a: \"unterminated\n")


class ShippedThemes(unittest.TestCase):
    """The two themes in themes/ must survive their own parser and stay sane."""

    def test_both_themes_parse_with_a_name_and_canvas(self):
        tdir = os.path.join(ROOT, "themes")
        names = sorted(f for f in os.listdir(tdir) if f.endswith(".yaml"))
        self.assertTrue(names, "no themes found")
        for fname in names:
            theme = t.load(os.path.join(tdir, fname))
            self.assertTrue(theme.get("name"), fname)
            self.assertTrue(t.is_hex(t.layer_hex(theme, "background")), fname)
            self.assertGreater(len(theme.get("customCSS") or ""), 500, fname)
            self.assertEqual(theme["name"], fname[:-5], "name must match the file name")
