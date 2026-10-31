"""Load skills (`skills/<name>/SKILL.md`) and their pre-activation rules (`preactivation.yaml`)."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog
import yaml

SKILLS_DIR = Path(__file__).parent / "skills"
SKILL_FILE = "SKILL.md"
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.DOTALL)
WORD_RE = re.compile(r"[a-z0-9]+")
INDEX_HEADER = "## Skills"
INDEX_INTRO = "Read a skill with `read_skill_file` before using its tools. Skills:"

log = structlog.get_logger()


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    allowed_tools: tuple[str, ...]
    path: str  # e.g. "answering-document-questions/SKILL.md"
    text: str  # whole file, exactly as `read_skill_file` returns it


@dataclass(frozen=True)
class ConditionRule:
    name: str  # tool name
    when: str  # condition name, resolved to a check by the middleware


@dataclass(frozen=True)
class SkillCatalog:
    skills: dict[str, Skill]
    skill_rules: tuple[tuple[str, tuple[str, ...]], ...]  # (skill name, trigger words)
    tool_rules: tuple[ConditionRule, ...]
    max_skills: int

    def system_prompt(self, base: str) -> str:
        """Base prompt plus the skill index (name, path, description per skill)."""
        index = "\n".join(f"- {s.name} (`{s.path}`): {s.description}" for s in self.skills.values())
        return f"{base.strip()}\n\n{INDEX_HEADER}\n{INDEX_INTRO}\n{index}\n"

    def preactivate(self, query: str) -> list[Skill]:
        """Skills whose trigger words appear in the query, in rule order, capped."""
        words = set(WORD_RE.findall(query.lower()))
        hits = {name: [t for t in triggers if t in words] for name, triggers in self.skill_rules}
        matched = {name: found for name, found in hits.items() if found}
        selected = list(matched)[: self.max_skills]
        log.info("preactivate", selected=selected, triggers=matched)
        return [self.skills[name] for name in selected]


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


def _skill_rules(
    path: Path, rules: list[dict[str, Any]], skills: dict[str, Skill]
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    parsed: list[tuple[str, tuple[str, ...]]] = []
    for rule in rules:
        name, triggers = rule.get("skill"), rule.get("triggers")
        if name not in skills:
            raise ValueError(f"{path}: unknown skill {name!r}; known {sorted(skills)}")
        if not isinstance(triggers, list) or not triggers:
            raise ValueError(f"{path}: {name}: triggers must be a non-empty list of words")
        # Queries are matched word by word, so a trigger with a space or punctuation never fires.
        words = tuple(str(t).strip().lower() for t in triggers)
        bad = [t for t in words if not WORD_RE.fullmatch(t)]
        if bad:
            raise ValueError(f"{path}: {name}: triggers must be single words, got {bad}")
        parsed.append((name, words))
    return tuple(parsed)


def _tool_rules(path: Path, rules: list[dict[str, Any]]) -> tuple[ConditionRule, ...]:
    parsed: list[ConditionRule] = []
    for rule in rules:
        tool, when = rule.get("tool"), rule.get("when")
        if not isinstance(tool, str) or not isinstance(when, str):
            raise ValueError(f"{path}: tool rules need string 'tool' and 'when', got {rule}")
        parsed.append(ConditionRule(tool, when))
    return tuple(parsed)


def load_skills(root: Path = SKILLS_DIR) -> SkillCatalog:
    """Read every `<name>/SKILL.md` and `preactivation.yaml`; fail fast on bad files."""
    skills = {
        s.name: s for s in (_load_skill(p, root) for p in sorted(root.glob(f"*/{SKILL_FILE}")))
    }
    if not skills:
        raise ValueError(f"{root}: no */{SKILL_FILE} files")
    path = root / "preactivation.yaml"
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError(f"{path}: must be a mapping")
    max_skills = config.get("max_skills")
    if not isinstance(max_skills, int) or max_skills < 1:
        raise ValueError(f"{path}: max_skills must be an int >= 1")
    catalog = SkillCatalog(
        skills=skills,
        skill_rules=_skill_rules(path, config.get("skills") or [], skills),
        tool_rules=_tool_rules(path, config.get("tools") or []),
        max_skills=max_skills,
    )
    log.info("skills_loaded", skills=list(skills), tool_rules=len(catalog.tool_rules))
    return catalog
