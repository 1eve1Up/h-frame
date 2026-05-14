"""Unit tests for license_engine (stdlib unittest + license_expression only)."""

from __future__ import annotations

import importlib.util
import unittest

if importlib.util.find_spec("license_expression") is None:
    raise unittest.SkipTest(
        "install tools/licensing/requirements.txt for license tests"
    )

from license_engine import validate_scan_code_json

# Minimal policy mirroring tools/licensing/license_policy.allowlist.yaml semantics.
_POLICY: dict = {
    "approved_spdx_license_identifiers": [
        "MIT",
        "Apache-2.0",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "ISC",
        "Python-2.0",
    ],
    "first_party_path_globs": [
        "src/**",
        "tests/**",
        "pyproject.toml",
        "README.md",
        "LICENSE",
        "tools/licensing/**",
        ".github/**",
    ],
    "allowed_license_ref_prefixes": ["LicenseRef-scancode-"],
    "options": {
        "allow_unknown_license_ref_tokens_on_first_party_paths": True,
        "allow_license_ref_tokens_outside_first_party": False,
    },
}


class TestValidateScanCodeJson(unittest.TestCase):
    def test_empty_report(self) -> None:
        self.assertEqual(validate_scan_code_json({"files": []}, _POLICY), [])

    def test_deep_src_path_first_party(self) -> None:
        data = {
            "files": [
                {
                    "type": "file",
                    "path": "src/hframe/native/shim.c",
                    "detected_license_expression_spdx": "Apache-2.0",
                }
            ]
        }
        self.assertEqual(validate_scan_code_json(data, _POLICY), [])

    def test_approved_mit_on_src_path(self) -> None:
        data = {
            "files": [
                {
                    "type": "file",
                    "path": "src/hframe/example.py",
                    "detected_license_expression_spdx": "MIT",
                }
            ]
        }
        self.assertEqual(validate_scan_code_json(data, _POLICY), [])

    def test_gpl_rejected(self) -> None:
        data = {
            "files": [
                {
                    "type": "file",
                    "path": "src/hframe/bad.py",
                    "detected_license_expression_spdx": "GPL-3.0-only",
                }
            ]
        }
        v = validate_scan_code_json(data, _POLICY)
        self.assertEqual(len(v), 1)
        self.assertIn("GPL-3.0-only", v[0][1])

    def test_license_ref_allowed_first_party(self) -> None:
        data = {
            "files": [
                {
                    "type": "file",
                    "path": "tools/licensing/validate_report.py",
                    "detected_license_expression_spdx": "LicenseRef-scancode-unknown",
                }
            ]
        }
        self.assertEqual(validate_scan_code_json(data, _POLICY), [])

    def test_unparseable_expression(self) -> None:
        data = {
            "files": [
                {
                    "type": "file",
                    "path": "README.md",
                    "detected_license_expression_spdx": "(((broken",
                }
            ]
        }
        v = validate_scan_code_json(data, _POLICY)
        self.assertTrue(any("unparseable" in r[2] for r in v))


if __name__ == "__main__":
    unittest.main()
