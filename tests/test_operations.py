from __future__ import annotations

from hframe.operations import default_policy_template


def test_default_policy_template_is_denylist_only_fallback() -> None:
    text = default_policy_template()
    assert "hframe-policy: mode denylist-only" in text
    assert "fallback" in text.lower()
