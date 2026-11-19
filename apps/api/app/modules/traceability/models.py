"""Traceability tables: project, project_artifact, trace_node, trace_edge (Architecture 6.3)."""

import enum
import uuid

from sqlalchemy import Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, RecordMixin
from app.db.types import fk


class NodeType(str, enum.Enum):
    requirement = "requirement"
    story = "story"
    acceptance_criterion = "acceptance_criterion"
    design_frame = "design_frame"
    endpoint = "endpoint"
    dev_task = "dev_task"
    test_case = "test_case"
    defect = "defect"


class Relation(str, enum.Enum):
    satisfies = "satisfies"
    designs = "designs"
    implements = "implements"
    verifies = "verifies"
    reveals = "reveals"


class EdgeOrigin(str, enum.Enum):
    tag = "tag"
    suggested = "suggested"
    manual = "manual"


class EdgeStatus(str, enum.Enum):
    proposed = "proposed"
    confirmed = "confirmed"
    rejected = "rejected"


class Project(RecordMixin, Base):
    __tablename__ = "project"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)


class ProjectArtifact(RecordMixin, Base):
    """The approved output of a role, linked to a submission."""

    __tablename__ = "project_artifact"

    project_id: Mapped[uuid.UUID] = fk("project")
    submission_id: Mapped[uuid.UUID] = fk("submission")
    role_key: Mapped[str] = mapped_column(String(50), nullable=False)


class TraceNode(RecordMixin, Base):
    __tablename__ = "trace_node"

    project_id: Mapped[uuid.UUID] = fk("project")
    type: Mapped[NodeType] = mapped_column(Enum(NodeType, name="node_type"), nullable=False)
    external_ref: Mapped[str] = mapped_column(String(200), nullable=False)  # e.g. REQ-012
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class TraceEdge(RecordMixin, Base):
    __tablename__ = "trace_edge"

    from_node_id: Mapped[uuid.UUID] = fk("trace_node")
    to_node_id: Mapped[uuid.UUID] = fk("trace_node")
    relation: Mapped[Relation] = mapped_column(Enum(Relation, name="relation"), nullable=False)
    status: Mapped[EdgeStatus] = mapped_column(
        Enum(EdgeStatus, name="edge_status"), default=EdgeStatus.proposed, nullable=False
    )
    confirmed_by: Mapped[uuid.UUID | None] = fk("user", nullable=True)
    origin: Mapped[EdgeOrigin] = mapped_column(Enum(EdgeOrigin, name="edge_origin"), nullable=False)
