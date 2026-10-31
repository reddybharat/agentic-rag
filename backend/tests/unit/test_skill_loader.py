from pathlib import Path

import pytest

from app.agent.skill_loader import INDEX_HEADER, load_skills

ANSWERING = "answering-document-questions"
SKILL_MD = "---\nname: {name}\ndescription: d\nallowed-tools: {tools}\n---\nbody\n"
PREACTIVATION = (
    "max_skills: 1\n"
    "skills:\n  - skill: s\n    triggers: [{triggers}]\n"
    "tools:\n  - tool: t\n    when: {when}\n"
)


def _write(
    root: Path, name: str = "s", tools: str = "t", triggers: str = "word", when: str = "always"
) -> Path:
    (root / "s").mkdir()
    (root / "s" / "SKILL.md").write_text(SKILL_MD.format(name=name, tools=tools))
    (root / "preactivation.yaml").write_text(PREACTIVATION.format(triggers=triggers, when=when))
    return root


def test_shipped_skills_are_indexed_under_the_base_prompt() -> None:
    catalog = load_skills()

    assert ANSWERING in catalog.skills
    assert catalog.skills[ANSWERING].allowed_tools == ("retrieve_documents",)
    prompt = catalog.system_prompt("Base prompt.")
    assert prompt.startswith("Base prompt.\n\n" + INDEX_HEADER)
    assert f"- {ANSWERING} (`{ANSWERING}/SKILL.md`):" in prompt
    assert "## Workflow" not in prompt  # skill bodies stay out until read
    assert [(r.name, r.when) for r in catalog.tool_rules] == [
        ("retrieve_documents", "library_has_documents")
    ]


def test_preactivate_matches_whole_words() -> None:
    catalog = load_skills()

    assert [s.name for s in catalog.preactivate("What is the budget?")] == [ANSWERING]
    assert catalog.preactivate("whatever happened") == []  # "what" only as a whole word
    assert catalog.preactivate("hello there") == []


def test_valid_minimal_skill_loads(tmp_path: Path) -> None:
    catalog = load_skills(_write(tmp_path))

    assert [s.path for s in catalog.skills.values()] == ["s/SKILL.md"]


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"name": "other"}, "must equal folder name"),
        ({"tools": "''"}, "allowed-tools"),
        ({"triggers": "'two words'"}, "single words"),
        ({"when": "[a]"}, "string 'tool' and 'when'"),
    ],
)
def test_invalid_files_are_rejected(tmp_path: Path, kwargs: dict[str, str], error: str) -> None:
    with pytest.raises(ValueError, match=error):
        load_skills(_write(tmp_path, **kwargs))


def test_missing_frontmatter_is_rejected(tmp_path: Path) -> None:
    _write(tmp_path)
    (tmp_path / "s" / "SKILL.md").write_text("no frontmatter")

    with pytest.raises(ValueError, match="frontmatter"):
        load_skills(tmp_path)
