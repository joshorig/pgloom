from __future__ import annotations

import pytest

from pgloom.prompts import (
    PromptRegistry,
    PromptTemplate,
    __all__,
)


def test_prompt_register_get_and_render() -> None:
    registry = PromptRegistry()
    template = PromptTemplate(name="demo", version="1", template="hello {name}")
    registry.register(template)
    assert registry.get("demo", "1") == template
    assert registry.render("demo", name="Ada") == "hello Ada"


def test_prompt_latest_version() -> None:
    registry = PromptRegistry()
    registry.register(PromptTemplate(name="demo", version="1", template="one"))
    registry.register(PromptTemplate(name="demo", version="2", template="two"))
    assert registry.get("demo").version == "2"


def test_prompt_unknown_raises() -> None:
    with pytest.raises(KeyError):
        PromptRegistry().get("missing")


def test_prompt_exports() -> None:
    assert set(__all__) == {"PromptRegistry", "PromptTemplate", "register_prompt", "render_prompt"}
