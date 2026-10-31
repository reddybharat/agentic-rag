---
name: {{verb-ing-object, e.g. comparing-documents}}
description: Read when the user {{the situation that makes this skill relevant}}. Use to {{the tasks it handles, in the user's words}}. {{What it does, in one sentence}}.
allowed-tools: {{tool_one}} {{tool_two}}
---
<!--
How to use this template
- Copy this file to backend/app/agent/skills/<name>/SKILL.md, fill every {{...}}, and delete all comments.
- name: gerund + object, kebab-case, at most 64 characters. Must equal the folder name.
- description: one line in the index the model always sees, so it alone decides when the skill is read.
  YAML: avoid a colon followed by a space inside it, or the file fails to load.
  Sentence 1 = when to read, sentence 2 = when to use, sentence 3 = what it does. About 300 characters.
- allowed-tools: space-separated tool names. Reading this file unlocks them for the rest of the turn.
  Each must exist in the tool list passed to build_agent (container.py), or startup fails.
- The whole file, frontmatter included, is returned by read_skill_file and resent on every model call
  in the turn. State each rule once; add an example only when it shows something the rules don't.
- Rules that apply to every turn, whichever skill is read, belong in agent/prompts/system.md, not here.

After adding a skill: run `uv run pytest tests/unit -q` in backend/ (the loader tests load every shipped
skill), then ask one question that should use it and check the read_skill_file and tool steps.
-->
# {{Skill title, e.g. Comparing documents}}

## Overview

{{The goal in one or two sentences.}} Done means {{what the user has at the end, including the empty case}}.

## Tools

- {{What it fetches}}: `{{tool_one}}({{arg}})`. Returns {{what comes back}}.
- {{What it fetches}}: `{{tool_two}}({{arg}})`. Returns {{what comes back}}.

## Rules

<!-- Hard constraints and facts the model can't work out alone. One rule per bullet, stated once. -->
- {{Constraint, e.g. "Answer only from the returned passages."}}
- {{When to ask the user for something and when not to}}
- {{Limits, e.g. "At most 4 calls to retrieve_from_documents."}}

## Workflow

<!-- Number the steps only if their order matters. Each step is one action. Put error handling specific to this skill here. -->
1. {{Get the input; what to ask if it's missing}}
2. Call `{{tool_one}}` with {{arguments}}.
3. Act on the result:
   - {{condition}}: {{what to answer}}
   - {{condition, e.g. nothing found}}: {{what to answer}}

## Answer formats

<!-- Default formats. Write "Use exactly this format" only when the format carries data the next step needs. -->
- **{{Case}}:** "{{Sentence with {FIELD} placeholders}}"
- **Nothing found:** "{{Sentence}}"

## Examples

<!-- At least two, including one edge case. Answers must follow the formats above word for word. -->

**{{Main case}}**
User: "{{Realistic message}}"
Call: `{{tool_one}}({{arg}}="{{value}}")` returns {{what comes back}}.
Answer: "{{Answer}}"

**{{Edge case: nothing found, ambiguous, or too many results}}**
User: "{{Message}}"
Call: `{{tool_one}}({{arg}}="{{value}}")` returns {{what comes back}}.
Answer: "{{Answer}}"
