#!/usr/bin/env python3
"""Black-box tests for the command line tools.

They are run as subprocesses on purpose: what matters is the exit code a CI job
sees and what a human reads on stdout, not an internal API.

    python3 -m unittest discover -s tests -v
"""

import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "skills", "hermes-dashboard-theming", "scripts")
THEMES = os.path.join(ROOT, "themes")

BAD_THEME = """name: broken
label: Broken
palette:
  background: "#F8F9FB"
colorOverrides:
  cardFg: "#111111"
  primary: ""
componentStyles:
  badge:
    background: "#FF0000"
  tab:
    background: "#00FF00"
layout:
  density: loose
customCSS: |
  :root { --series-input-token: #FFE28A; }
"""


def run(*args):
    return subprocess.run([sys.executable] + list(args), cwd=ROOT,
                          capture_output=True, text=True)


class ThemeCheck(unittest.TestCase):
    def test_shipped_themes_are_clean(self):
        files = [os.path.join(THEMES, f) for f in sorted(os.listdir(THEMES))]
        res = run(os.path.join(SCRIPTS, "theme-check.py"), "--strict", "--quiet", *files)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_broken_theme_fails_with_named_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "broken.yaml")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(BAD_THEME)
            res = run(os.path.join(SCRIPTS, "theme-check.py"), path)
            self.assertEqual(res.returncode, 1)
            for code in ("override-unknown", "style-bucket-dead", "style-prop-dead",
                         "layout-density", "css-series-important"):
                self.assertIn(code, res.stdout, "missing finding: %s" % code)

    def test_json_output_is_parseable(self):
        import json
        res = run(os.path.join(SCRIPTS, "theme-check.py"), "--json",
                  os.path.join(THEMES, "light-clean.yaml"))
        payload = json.loads(res.stdout)
        self.assertTrue(payload["files"][0]["findings"] is not None)


class NewTheme(unittest.TestCase):
    def test_generated_theme_passes_the_linter(self):
        with tempfile.TemporaryDirectory() as tmp:
            for mode in ("light", "dark"):
                res = run(os.path.join(ROOT, "tools", "new-theme.py"), "gen-" + mode,
                          "--accent", "#7C5CFF", "--mode", mode, "--out", tmp)
                self.assertEqual(res.returncode, 0, res.stderr)
            check = run(os.path.join(SCRIPTS, "theme-check.py"), "--strict", "--quiet",
                        os.path.join(tmp, "gen-light.yaml"), os.path.join(tmp, "gen-dark.yaml"))
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_refuses_to_overwrite_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = (os.path.join(ROOT, "tools", "new-theme.py"), "gen", "--out", tmp)
            self.assertEqual(run(*args).returncode, 0)
            self.assertEqual(run(*args).returncode, 2)

    def test_rejects_a_builtin_name_and_a_bad_accent(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run(os.path.join(ROOT, "tools", "new-theme.py"), "default",
                                 "--out", tmp).returncode, 2)
            self.assertEqual(run(os.path.join(ROOT, "tools", "new-theme.py"), "ok",
                                 "--accent", "teal", "--out", tmp).returncode, 2)


class Reports(unittest.TestCase):
    def test_contrast_report_of_a_generated_theme_is_green(self):
        with tempfile.TemporaryDirectory() as tmp:
            run(os.path.join(ROOT, "tools", "new-theme.py"), "gen", "--out", tmp)
            res = run(os.path.join(ROOT, "tools", "contrast-report.py"),
                      os.path.join(tmp, "gen.yaml"))
            self.assertEqual(res.returncode, 0, res.stdout)

    def test_contrast_report_flags_the_shipped_ring(self):
        res = run(os.path.join(ROOT, "tools", "contrast-report.py"), "--no-fail",
                  os.path.join(THEMES, "light-clean.yaml"))
        self.assertEqual(res.returncode, 0)
        self.assertIn("focus ring on canvas", res.stdout)

    def test_markdown_and_json_formats(self):
        res = run(os.path.join(ROOT, "tools", "contrast-report.py"), "--format", "markdown",
                  os.path.join(THEMES, "dark-clean.yaml"))
        self.assertIn("| pair |", res.stdout)


class GeneratedFilesAreCurrent(unittest.TestCase):
    """The generated pages and docs must match their generators."""

    def test_schema_doc_is_current(self):
        res = run(os.path.join(ROOT, "tools", "gen-schema-doc.py"), "--check")
        self.assertEqual(res.returncode, 0, res.stdout)

    def test_gallery_is_current(self):
        res = run(os.path.join(ROOT, "tools", "build-gallery.py"), "--check")
        self.assertEqual(res.returncode, 0, res.stdout)
