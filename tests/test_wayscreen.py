#!/usr/bin/env python3
"""Unit tests for wayscreen (stdlib only, no extra dependencies).

Run from the repo root:
    python3 -m unittest discover -s tests -v
"""
import importlib.machinery
import importlib.util
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "wayscreen")

# Isolate config/profiles I/O from the real user config before importing.
_TMP = tempfile.TemporaryDirectory()
os.environ["WAYSCREEN_CONFIG_DIR"] = _TMP.name

_loader = importlib.machinery.SourceFileLoader("wayscreen", SCRIPT)
_spec = importlib.util.spec_from_loader("wayscreen", _loader)
ws = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ws)


def _fresh_dirs(testcase):
    """Point the module's config dirs at a fresh temp dir for this test.

    Note: CONFIG_FILE/PROFILES_DIR are computed at import time from
    CONFIG_DIR, so all three must be overridden for real isolation."""
    d = tempfile.TemporaryDirectory()
    testcase.addCleanup(d.cleanup)
    ws.CONFIG_DIR = d.name
    ws.CONFIG_FILE = os.path.join(d.name, "config.json")
    ws.PROFILES_DIR = os.path.join(d.name, "profiles")


class TestTempWeights(unittest.TestCase):
    def test_neutral_at_6500(self):
        r, g, b = ws._temp_weights(6500)
        self.assertAlmostEqual(r, 1.0, places=6)
        self.assertAlmostEqual(g, 1.0, places=6)
        self.assertAlmostEqual(b, 1.0, places=6)

    def test_warm_boosts_red(self):
        r, g, b = ws._temp_weights(2000)
        self.assertGreater(r, g)
        self.assertGreater(g, b)

    def test_cool_boosts_blue(self):
        r, g, b = ws._temp_weights(9000)
        self.assertGreater(b, g)
        self.assertGreater(g, r)

    def test_weights_stay_in_unit_range(self):
        for t in (1, 1000, 3000, 6500, 10000, 40000, 999999):
            for v in ws._temp_weights(t):
                self.assertGreaterEqual(v, 0.0)
                self.assertLessEqual(v, 1.0)


class TestEstimateTemp(unittest.TestCase):
    def test_roundtrip_known_temperatures(self):
        for t in (2000, 3500, 5000, 6500, 8000, 9500):
            with self.subTest(t=t):
                est = ws._estimate_temp(*ws._temp_weights(t))
                self.assertLessEqual(abs(est - t), 50)

    def test_cold_and_warm_are_distinguishable(self):
        cold = ws._estimate_temp(*ws._temp_weights(2500))
        warm = ws._estimate_temp(*ws._temp_weights(9000))
        self.assertLess(cold, warm)


class TestConfigIO(unittest.TestCase):
    def setUp(self):
        _fresh_dirs(self)

    def test_roundtrip(self):
        vals = {"Brightness": 0.42, "Temperature": 4200, "Gamma": 1.3}
        ws.save_config(vals)
        self.assertEqual(ws.load_config(), vals)

    def test_missing_config_returns_empty(self):
        self.assertEqual(ws.load_config(), {})

    def test_corrupt_config_returns_empty(self):
        with open(os.path.join(ws.CONFIG_DIR, "config.json"), "w") as f:
            f.write("{definitely not json")
        self.assertEqual(ws.load_config(), {})

    def test_unwritable_dir_does_not_raise(self):
        ws.CONFIG_DIR = "/proc/forbidden"
        ws.save_config({"Brightness": 1.0})  # must not raise
        self.assertEqual(ws.load_config(), {})


class TestProfiles(unittest.TestCase):
    def setUp(self):
        _fresh_dirs(self)

    def test_empty_when_no_profiles(self):
        self.assertEqual(ws.list_profiles(), [])

    def test_save_list_load_delete(self):
        ws.save_profile("day", {"Brightness": 1.0, "Temperature": 6500, "Gamma": 1.0})
        ws.save_profile("night", {"Brightness": 0.3, "Temperature": 4000, "Gamma": 1.1})
        self.assertEqual(ws.list_profiles(), ["day", "night"])
        self.assertEqual(ws.load_profile("night")["Temperature"], 4000)
        self.assertEqual(ws.load_profile("missing"), {})

        ws.delete_profile("day")
        self.assertEqual(ws.list_profiles(), ["night"])
        ws.delete_profile("also-missing")  # must be a silent no-op


class TestWriter(unittest.TestCase):
    def test_pending_writes_coalesce_and_overwrite(self):
        calls = []
        original = ws.set_val
        ws.set_val = lambda prop, typ, val: calls.append((prop, typ, val))
        self.addCleanup(setattr, ws, "set_val", original)

        w = ws._Writer()
        w.push("Brightness", "d", 0.5)
        w.push("Temperature", "q", 4000)
        w.push("Brightness", "d", 0.7)  # overwrites the earlier Brightness
        w.flush_now()
        self.assertEqual(calls, [("Brightness", "d", 0.7), ("Temperature", "q", 4000)])

    def test_flush_with_nothing_pending_is_noop(self):
        w = ws._Writer()
        w.flush_now()  # must not raise


class TestCli(unittest.TestCase):
    def setUp(self):
        self._old_argv = sys.argv

    def tearDown(self):
        sys.argv = self._old_argv

    def _run(self, argv):
        sys.argv = argv
        with redirect_stdout(io.StringIO()):
            return ws._cli_mode()

    def test_no_cli_flags_returns_none(self):
        self.assertIsNone(self._run(["wayscreen"]))

    def test_status_returns_zero(self):
        self.assertEqual(self._run(["wayscreen", "--status"]), 0)

    def test_get_unknown_property_rejected(self):
        self.assertEqual(self._run(["wayscreen", "--get", "nope"]), 2)

    def test_get_missing_value_rejected(self):
        self.assertEqual(self._run(["wayscreen", "--get"]), 2)

    def test_set_unknown_property_rejected(self):
        self.assertEqual(self._run(["wayscreen", "--set", "nope=1"]), 2)

    def test_set_invalid_value_rejected(self):
        self.assertEqual(self._run(["wayscreen", "--set", "brightness=abc"]), 2)

    def test_set_clamps_out_of_range_values(self):
        calls = []
        original = ws.set_val
        def fake_set_val(prop, typ, val):
            calls.append((prop, typ, val))
            return 0
        ws.set_val = fake_set_val
        self.addCleanup(setattr, ws, "set_val", original)

        self.assertEqual(self._run(["wayscreen", "--set", "brightness=500"]), 0)
        self.assertEqual(self._run(["wayscreen", "--set", "temperature=99999"]), 0)
        self.assertEqual(self._run(["wayscreen", "--set", "gamma=9"]), 0)
        self.assertEqual(calls, [
            ("Brightness", "d", 1.0),
            ("Temperature", "q", 10000),
            ("Gamma", "d", 3.0),
        ])

    def test_set_reports_failed_write(self):
        original = ws.set_val
        ws.set_val = lambda prop, typ, val: 1  # busctl would fail
        self.addCleanup(setattr, ws, "set_val", original)
        self.assertEqual(self._run(["wayscreen", "--set", "brightness=50"]), 1)

    def test_unknown_flag_rejected(self):
        self.assertEqual(self._run(["wayscreen", "--frobnicate"]), 2)

    def test_positional_junk_rejected(self):
        self.assertEqual(self._run(["wayscreen", "hello"]), 2)

    def test_get_and_set_together_rejected(self):
        self.assertEqual(
            self._run(["wayscreen", "--get", "gamma", "--set", "temperature=4000"]), 2)

    def test_help_prints_usage(self):
        self.assertEqual(self._run(["wayscreen", "--help"]), 0)

    def test_set_missing_value_rejected(self):
        self.assertEqual(self._run(["wayscreen", "--set"]), 2)


if __name__ == "__main__":
    unittest.main()
