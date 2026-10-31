"""Load skills (`skills/<name>/SKILL.md`) and build the skill index for the system prompt."""

import re
from dataclasses import dataclass
from pathlib import Path

import structlog
import yaml

SKILLS_DIR = Path(__file__).parent / "skills"
SKILL_FILE = "SKILL.md"
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.DOTALL)
INDEX_HEADER = "## Skills"
INDEX_INTRO = "Available skills:"

log = structlog.get_logger()


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    allowed_tools: tuple[str, ...]
    path: str  # e.g. "retrieving-from-documents/SKILL.md"
    text: str  # whole file, exactly as `read_skill_file` returns it


@dataclass(frozen=True)
class SkillCatalog:
    skills: dict[str, Skill]

    def system_prompt(self, base: str) -> str:
        """Base prompt plus the skill index (name, path, description, tools per skill)."""
        index = "\n".join(
            f"- {s.name} (`{s.path}`): {s.description} Tools: {' '.join(s.allowed_tools)}"
            for s in self.skills.values()
        )
        return f"{base.strip()}\n\n{INDEX_HEADER}\n{INDEX_INTRO}\n{index}\n"


def _load_skill(path: Path, root: Path) -> Skill:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(f"{path}: missing '---' frontmatter block")
    header = yaml.safe_load(match.group(1))
    if not isinstance(header, dict):
        raise ValueError(f"{path}: frontmatter must be a mapping")
    for key in ("name", "description"):
        value = header.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{path}: {key} must be a non-empty string")
    if header["name"] != path.parent.name:
        raise ValueError(
            f"{path}: name {header['name']!r} must equal folder name {path.parent.name!r}"
        )
    allowed_tools = header.get("allowed-tools")
    if not isinstance(allowed_tools, str) or not allowed_tools.split():
        raise ValueError(f"{path}: allowed-tools must be a non-empty space-separated string")
    return Skill(
        name=header["name"],
        description=header["description"].strip(),
        allowed_tools=tuple(allowed_tools.split()),
        path=path.relative_to(root).as_posix(),
        text=text,
    )


def load_skills(root: Path = SKILLS_DIR) -> SkillCatalog:
    """Read every `<name>/SKILL.md`; fail fast on bad files."""
    skills = {
        s.name: s for s in (_load_skill(p, root) for p in sorted(root.glob(f"*/{SKILL_FILE}")))
    }
    if not skills:
        raise ValueError(f"{root}: no */{SKILL_FILE} files")
    log.info("skills_loaded", skills=list(skills))
    return SkillCatalog(skills=skills)
