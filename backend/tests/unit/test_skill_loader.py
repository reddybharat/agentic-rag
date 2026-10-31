from pathlib import Path

import pytest

from app.agent.skill_loader import INDEX_HEADER, INDEX_INTRO, load_skills

RETRIEVING = "retrieving-from-documents"
SKILL_MD = "---\nname: {name}\ndescription: d\nallowed-tools: {tools}\n---\nbody\n"


def _write(root: Path, name: str = "s", tools: str = "t") -> Path:
    (root / "s").mkdir()
    (root / "s" / "SKILL.md").write_text(SKILL_MD.format(name=name, tools=tools))
    return root


def test_shipped_skills_are_indexed_under_the_base_prompt() -> None:
    catalog = load_skills()

    assert list(catalog.skills) == [RETRIEVING]
    assert catalog.skills[RETRIEVING].allowed_tools == ("retrieve_from_documents",)
    prompt = catalog.system_prompt("Base prompt.")
    assert prompt.startswith(f"Base prompt.\n\n{INDEX_HEADER}\n{INDEX_INTRO}\n")
    assert f"- {RETRIEVING} (`{RETRIEVING}/SKILL.md`):" in prompt
    assert prompt.rstrip().endswith("Tools: retrieve_from_documents")
    assert "## How to answer" not in prompt  # skill bodies stay out until read


def test_valid_minimal_skill_loads(tmp_path: Path) -> None:
    catalog = load_skills(_write(tmp_path))

    assert [s.path for s in catalog.skills.values()] == ["s/SKILL.md"]
    assert catalog.system_prompt("B").endswith("- s (`s/SKILL.md`): d Tools: t\n")


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"name": "other"}, "must equal folder name"),
        ({"tools": "''"}, "allowed-tools"),
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


def test_empty_skills_dir_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"no \*/SKILL.md"):
        load_skills(tmp_path)
