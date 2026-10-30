import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

from gpt_niang_linux.paths import resolve_executable
from gpt_niang_linux.protocol import Decoder, MAX_LINE, ProtocolError
from gpt_niang_linux.settings import Settings, normalize

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("kde_rules", ROOT / "integrations/kde/rules.py")
rules = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rules)


class SettingsTests(unittest.TestCase):
    def test_atomic_round_trip_and_bounds(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested/settings.json"
            settings = Settings(path)
            settings.save(scale=8, codexPath="/a path/codex", quotesEnabled=False)
            self.assertEqual(Settings(path).values["scale"], 2.5)
            self.assertEqual(Settings(path).values["codexPath"], "/a path/codex")
            self.assertFalse(Settings(path).values["quotesEnabled"])
            self.assertEqual(list(path.parent.glob(".settings-*")), [])
            self.assertNotIn("windows", json.loads(path.read_text()))

    def test_corrupt_and_future_schema_are_preserved(self):
        for contents in ("bad json", '[1]', '{"schemaVersion":2}', '{"scale": NaN}'):
            with self.subTest(contents=contents), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "settings.json"
                path.write_text(contents)
                settings = Settings(path)
                self.assertEqual(settings.values["scale"], 1)
                if contents != '{"scale": NaN}':
                    self.assertTrue(settings.warning)
                    self.assertEqual(len(list(path.parent.glob("settings.corrupt-*"))), 1)

    def test_invalid_scalar_values_do_not_escape_validation(self):
        self.assertEqual(normalize({"scale": True, "nodePath": "x\0y", "quotesEnabled": 4})["scale"], 1)
        self.assertEqual(normalize({"scale": -2})["scale"], 0.6)


class ProtocolTests(unittest.TestCase):
    def test_split_utf8_and_multiple_messages(self):
        data = (json.dumps({"schemaVersion": 1, "type": "error", "requestId": "1", "message": "中文"}, ensure_ascii=False) + "\n").encode()
        decoder = Decoder()
        output = []
        for byte in data:
            output.extend(decoder.feed(bytes([byte])))
        self.assertEqual(output[0]["message"], "中文")
        self.assertEqual(len(decoder.feed(data + data)), 2)

    def test_bad_envelopes_and_size_limit(self):
        for line in (b"oops\n", b"[]\n", b'{"schemaVersion":2,"type":"snapshot"}\n', b'{"schemaVersion":1,"type":"unknown"}\n', b"x" * (MAX_LINE + 1)):
            with self.subTest(line=line[:20]), self.assertRaises(ProtocolError):
                Decoder().feed(line)


class PathsTests(unittest.TestCase):
    def test_stale_nvm_path_recovers_with_minimal_path_and_spaces(self):
        with tempfile.TemporaryDirectory(prefix="pet path ") as directory:
            root = Path(directory)
            for version in ("v9.0.0", "v24.1.0", "v24.10.0"):
                candidate = root / ".nvm/versions/node" / version / "bin/codex"
                candidate.parent.mkdir(parents=True)
                candidate.write_text("#!/bin/sh\nexit 0\n")
                candidate.chmod(0o755)
            found = resolve_executable("codex", "/missing/codex", env={"PATH": str(root)}, home=root)
            self.assertIn("v24.10.0", found)
            self.assertEqual(resolve_executable("codex", found, env={"PATH": ""}, home=root), found)


class RulesTests(unittest.TestCase):
    def test_install_preserves_unrelated_sections_and_removes_only_own_rule(self):
        unrelated = "[another-window]\nDescription=My settings\nposition=3,4\npositionrule=2\n# keep this comment\n"
        original = "# header\n[General]\ncount=1\nrules=another-window\n" + unrelated
        installed = rules.update(original)
        self.assertIn(unrelated, installed)
        self.assertIn("positionrule=4", installed)
        self.assertNotIn("sizerule=", installed)
        self.assertIn("title=GPT-Niang Pet\ntitlematch=1", installed)
        removed = rules.update(installed, remove=True)
        self.assertIn(unrelated, removed)
        self.assertNotIn(rules.GROUP, removed)
        self.assertIn("rules=another-window", removed)

    def test_repeat_install_keeps_remembered_coordinates(self):
        installed = rules.update("").replace("position=40,40", "position=723,144")
        self.assertEqual(rules.update(installed), installed)

    def test_legacy_groups_and_conflicts(self):
        legacy = "[General]\ncount=2\n[1]\nDescription=A\n[2]\nDescription=B\n"
        self.assertIn("rules=" + rules.GROUP + ",1,2", rules.update(legacy))
        with self.assertRaises(ValueError):
            rules.update("[" + rules.GROUP + "]\nDescription=someone else\n")


if __name__ == "__main__":
    unittest.main()
