import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase, override_settings

from utils import clear_and_load_fixtures as clf


class ClearAndLoadFixturesExtraTests(TestCase):
    def test_confirm_yes_and_no(self):
        with patch("builtins.input", return_value="y"):
            self.assertTrue(clf.confirm("prompt"))
        with patch("builtins.input", return_value="n"):
            self.assertFalse(clf.confirm("prompt"))

    def test_check_safety_flags_blocks_in_prod_without_force(self):
        with override_settings(DEBUG=False):
            with patch.dict("os.environ", {}, clear=True):
                with self.assertRaises(SystemExit):
                    clf.check_safety_flags(force=False)

    def test_verify_fixture_file_missing_exits(self):
        p = Path(tempfile.gettempdir()) / "no_such_fixture_12345.json"
        if p.exists():
            p.unlink()
        with self.assertRaises(SystemExit):
            clf.verify_fixture_file(p)

    def test_load_fixtures_handles_permission_error_and_creates_noperms(self):
        data = [
            {"model": "auth.permission", "pk": 1, "fields": {}},
            {"model": "Users.user", "pk": 1, "fields": {}},
        ]
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".json", delete=False, encoding="utf-8"
        ) as fh:
            json.dump(data, fh, ensure_ascii=False)
            path = Path(fh.name)
        try:

            def side_effect_loaddata(*args, **kwargs):
                if len(side_effect_loaddata.calls) == 0:
                    side_effect_loaddata.calls.append(1)
                    raise Exception("Permission has no content_type for some reason")
                return None

            side_effect_loaddata.calls = []
            with patch(
                "utils.clear_and_load_fixtures.call_command",
                side_effect=side_effect_loaddata,
            ) as mock_call:
                clf.load_fixtures(path, verbosity=0)
                self.assertGreaterEqual(mock_call.call_count, 2)
        finally:
            try:
                path.unlink()
            except Exception:
                pass
            try:
                tmp = path.with_suffix(".noperms.json")
                tmp.unlink()
            except Exception:
                pass
