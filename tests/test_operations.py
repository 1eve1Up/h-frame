from __future__ import annotations

from hframe.operations import default_policy_template


def test_default_policy_allowlist_preserves_devcontainer_metadata() -> None:
    text = default_policy_template()
    assert ".devcontainer/**" in text
    assert ".devcontainer.json" in text
