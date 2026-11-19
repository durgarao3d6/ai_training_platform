"""Content file models and bundle reader (FR-CAT-01, FR-CAT-04).

Used only by the one-time import (catalog/loader.py); content is otherwise authored in the app.

Layout under content/:
  courses/<key>.yaml    course with its milestones
  tasks/<track>.yaml    task templates as {"tasks": [...]}, or one task per file
                        (JSON Schema: task-template.schema.json)
  rubrics/<id>.json     rubric version  (JSON Schema: rubric.schema.json)
  starters/             starter files handed to interns (referenced by tasks)
  drafts/               authoring drafts; never validated or loaded

Cross-file rules checked here:
- every course names an existing role profile
- every task names an existing milestone
- a demo task's rubric exists and belongs to the same role profile as its course (FR-EVAL-07)
- a role profile only lists checkers registered for that role
"""

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.content.validator import (
    find_contracts_dir,
    load_document,
    validate_rubric,
    validate_task_template,
)

RoleKey = Literal["developer", "ba", "qa", "uiux"]
CONTENT_SUFFIXES = {".json", ".yml", ".yaml"}

# Manifest for tasks that define no deliverables of their own and have no published rubric
# (content-only milestones): one piece of work as a file, a link or pasted text.
DEFAULT_DELIVERABLES: list[dict[str, Any]] = [
    {
        "id": "work",
        "title": "Your work",
        "kind": ["file", "link", "text"],
        "accept": [
            ".pdf",
            ".docx",
            ".md",
            ".txt",
            ".png",
            ".jpg",
            ".zip",
            ".py",
            ".yaml",
            ".yml",
            ".csv",
            ".json",
        ],
        "required": True,
        "description": "Hand in what the brief asks for as a file, a link or pasted text.",
    }
]

# PRD section 6. Enforced when a course is marked approved (tech lead decision 1).
EXPECTED_MILESTONES: dict[str, int] = {"developer": 10, "ba": 9, "qa": 10, "uiux": 9}


def _prerequisite_errors(course: "CourseContent") -> list[str]:
    """Prerequisites must name milestones in the same course and must not form a cycle."""
    keys = {m.key for m in course.milestones}
    graph = {m.key: m.prerequisites for m in course.milestones}
    errors = [
        f"milestone '{m.key}': unknown prerequisite '{p}'"
        for m in course.milestones
        for p in m.prerequisites
        if p not in keys
    ]
    state: dict[str, int] = {}  # 1 = visiting, 2 = done

    def visit(node: str, path: list[str]) -> None:
        if state.get(node) == 2:
            return
        if state.get(node) == 1:
            errors.append(f"prerequisite cycle: {' -> '.join([*path, node])}")
            return
        state[node] = 1
        for nxt in graph.get(node, []):
            if nxt in keys:
                visit(nxt, [*path, node])
        state[node] = 2

    for key in graph:
        visit(key, [])
    return errors


def _approval_errors(course: "CourseContent", task_modules: set[str]) -> list[str]:
    """Checks that apply only once a role expert has approved the track."""
    errors: list[str] = []
    expected = EXPECTED_MILESTONES[course.role_profile]
    if len(course.milestones) != expected:
        errors.append(
            f"approved course needs exactly {expected} milestones, has {len(course.milestones)}"
        )
    for m in course.milestones:
        if not m.description.strip():
            errors.append(f"milestone '{m.key}': description is required for an approved course")
        if not m.learning_objective.strip():
            errors.append(
                f"milestone '{m.key}': learning_objective is required for an approved course"
            )
        if m.key not in task_modules:
            errors.append(f"milestone '{m.key}': no task defined for an approved course")
    return errors


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RoleContent(_Strict):
    key: RoleKey
    name: str = Field(min_length=1)
    checkers: list[str]
    judge_prompt: str | None = None
    review_policy: dict[str, Any] = Field(default_factory=dict)


class MilestoneContent(_Strict):
    """Milestone contract (tech lead decision 1). Deliverables and evaluation depth live on the task."""

    key: str = Field(pattern=r"^[a-z0-9_.]+$")
    title: str = Field(min_length=1)
    position: int = Field(ge=1)
    description: str = ""
    learning_objective: str = ""
    prerequisites: list[str] = Field(default_factory=list)  # milestone keys in the same course
    competencies: list[str] = Field(default_factory=list)


class CourseContent(_Strict):
    key: str = Field(pattern=r"^[a-z0-9_.]+$")
    title: str = Field(min_length=1)
    role_profile: RoleKey
    review_status: Literal["draft", "approved"] = "draft"
    source: str = ""  # where titles and descriptions came from
    description: str = ""
    final_deliverable: str = ""
    milestones: list[MilestoneContent] = Field(default_factory=list)


def rubric_hash(doc: dict[str, Any]) -> str:
    """Content hash of a rubric. The same file always yields the same version."""
    canonical = json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass
class ContentBundle:
    roles: dict[str, RoleContent] = field(default_factory=dict)
    courses: dict[str, CourseContent] = field(default_factory=dict)
    tasks: dict[str, dict[str, Any]] = field(default_factory=dict)
    rubrics: dict[str, dict[str, Any]] = field(default_factory=dict)  # rubric_id -> doc


class ContentError(Exception):
    def __init__(self, errors: list[str]) -> None:
        super().__init__(f"{len(errors)} content error(s)")
        self.errors = errors


def _files(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.rglob("*") if p.suffix in CONTENT_SUFFIXES)


def read_bundle(root: Path, contracts: Path | None = None) -> ContentBundle:
    """Read and validate every content file. Raises ContentError listing all problems."""
    contracts = contracts or find_contracts_dir()
    registry: dict[str, list[str]] = json.loads(
        (contracts / "checkers.json").read_text(encoding="utf-8")
    )
    bundle = ContentBundle()
    errors: list[str] = []

    def parse(path: Path) -> Any:
        try:
            return load_document(path)
        except Exception as exc:  # noqa: BLE001 - report any parse failure with its file
            errors.append(f"{path}: cannot parse: {exc}")
            return None

    # Role profiles are defined in code (catalog/roles.py); their checkers are code plugins.
    from app.modules.catalog.roles import ROLE_PROFILES

    for key, spec in ROLE_PROFILES.items():
        bundle.roles[key] = RoleContent(
            key=cast(RoleKey, key),
            name=spec["name"],
            checkers=registry.get(key, []),
            review_policy=spec["review_policy"],
        )

    milestone_keys: dict[str, str] = {}  # milestone key -> course key
    for path in _files(root / "courses"):
        doc = parse(path)
        if doc is None:
            continue
        try:
            course = CourseContent.model_validate(doc)
        except ValidationError as exc:
            errors.append(f"{path}: {exc}")
            continue
        if course.key in bundle.courses:
            errors.append(f"{path}: duplicate course '{course.key}'")
        if course.role_profile not in bundle.roles:
            errors.append(f"{path}: unknown role profile '{course.role_profile}'")
        positions = [m.position for m in course.milestones]
        if len(set(positions)) != len(positions):
            errors.append(f"{path}: duplicate milestone positions")
        for m in course.milestones:
            if m.key in milestone_keys:
                errors.append(
                    f"{path}: milestone key '{m.key}' already used in '{milestone_keys[m.key]}'"
                )
            milestone_keys[m.key] = course.key
        bundle.courses[course.key] = course

    for path in _files(root / "rubrics"):
        doc = parse(path)
        if doc is None:
            continue
        report = validate_rubric(doc, contracts)
        if not report.ok:
            errors.extend(f"{path}: {e}" for e in report.errors)
            continue
        if doc["rubric_id"] in bundle.rubrics:
            errors.append(f"{path}: duplicate rubric '{doc['rubric_id']}'")
        bundle.rubrics[doc["rubric_id"]] = doc

    for path in _files(root / "tasks"):
        file_doc = parse(path)
        if file_doc is None:
            continue
        # A file holds one task, or a track's tasks as {"tasks": [...]}.
        docs = (
            file_doc["tasks"] if isinstance(file_doc, dict) and "tasks" in file_doc else [file_doc]
        )
        for index, doc in enumerate(docs):
            where = f"{path}[{index}]" if len(docs) > 1 else str(path)
            report = validate_task_template(doc, contracts)
            if not report.ok:
                errors.extend(f"{where}: {e}" for e in report.errors)
                continue
            course_key = milestone_keys.get(doc["module"])
            if course_key is None:
                errors.append(f"{where}: unknown milestone '{doc['module']}'")
            rubric_id = doc.get("rubric")
            if rubric_id is not None:
                rubric = bundle.rubrics.get(rubric_id)
                if rubric is None:
                    errors.append(f"{where}: unknown rubric '{rubric_id}'")
                elif (
                    course_key is not None
                    and rubric["role_profile"] != bundle.courses[course_key].role_profile
                ):
                    errors.append(
                        f"{where}: rubric '{rubric_id}' belongs to role '{rubric['role_profile']}', "
                        f"but the task's course is role '{bundle.courses[course_key].role_profile}'"
                    )
            if rubric_id is not None and rubric_id in bundle.rubrics and "deliverables" in doc:
                rubric_deliverables = bundle.rubrics[rubric_id].get("deliverables")
                if rubric_deliverables is not None and doc["deliverables"] != rubric_deliverables:
                    errors.append(
                        f"{where}: deliverables differ from rubric '{rubric_id}'; keep one manifest"
                    )
            for starter in doc.get("starter_files", []):
                if not (root / "starters" / starter).is_file():
                    errors.append(
                        f"{where}: starter file 'content/starters/{starter}' does not exist"
                    )
            if doc["key"] in bundle.tasks:
                errors.append(f"{where}: duplicate task '{doc['key']}'")
            bundle.tasks[doc["key"]] = doc

    task_modules = {t["module"] for t in bundle.tasks.values()}
    for course in bundle.courses.values():
        errors.extend(f"course '{course.key}': {e}" for e in _prerequisite_errors(course))
        if course.review_status == "approved":
            errors.extend(
                f"course '{course.key}': {e}" for e in _approval_errors(course, task_modules)
            )

    if errors:
        raise ContentError(errors)
    return bundle
