# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import datetime

from typing import Optional

from sqlalchemy import (
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    text,
    func,
)
from sqlalchemy.dialects.postgresql import (
    ENUM,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from un0.wkflw.enums import (  # type: ignore
    WorkflowRecordStatus,
    WorkflowRecordState,
    WorkflowFlag,
    WorkflowDBEvent,
    WorkflowTrigger,
)
from un0.db import Base, BaseMixin, RBACMixin, str_26, str_255  # type: ignore
from un0.rltd.models import RelatedObject, TableType
from un0.fltr.models import Query


class Workflow(Base):
    __tablename__ = "workflow"
    __table_args__ = {
        "schema": "un0",
        "comment": "User-defined workflows",
        "info": {"rls_policy": "superuser", "in_graph": False},
    }

    id: Mapped[int] = mapped_column(
        Identity(start=1, cycle=False),
        primary_key=True,
        index=True,
        doc="Primary Key",
    )
    name: Mapped[str_255] = mapped_column(doc="Name of the workflow")
    explanation: Mapped[str] = mapped_column(
        doc="Explanation of the workflow indicating the purpose and the expected outcome"
    )
    trigger: Mapped[WorkflowTrigger] = mapped_column(
        ENUM(
            WorkflowTrigger,
            name="workflowtrigger",
            create_type=True,
            schema="un0",
        ),
        default=WorkflowTrigger.DB_EVENT,
        doc="The type of event that triggers execution of the workflow",
    )
    repeat_every: Mapped[int] = mapped_column(
        server_default=text("0"), doc="Repeat every x days"
    )
    flag: Mapped[WorkflowFlag] = mapped_column(
        ENUM(
            WorkflowFlag,
            name="workflowflag",
            create_type=True,
            schema="un0",
        ),
        default=WorkflowFlag.MEDIUM,
        doc="Flag indicating the importance of the workflow",
    )
    due_within: Mapped[int] = mapped_column(
        server_default=text("7"), doc="Due within x days"
    )
    db_event: Mapped[WorkflowDBEvent] = mapped_column(
        ENUM(
            WorkflowDBEvent,
            name="workflowdbevent",
            create_type=True,
            schema="un0",
        ),
        default=WorkflowDBEvent.INSERT,
        doc="The database event that triggers the workflow, if applicable",
    )
    auto_run: Mapped[bool] = mapped_column(
        server_default=text("false"),
        doc="Indicates if the workflow should be run automatically",
    )
    record_required: Mapped[bool] = mapped_column(
        server_default=text("false"), doc="Indicats if a Workflow Record is required"
    )
    limiting_query_id: Mapped[Optional[str_26]] = mapped_column(
        ForeignKey(
            "un0.query.id",
            ondelete="SET NULL",
            name="fk_workflow_query_id",
        ),
        index=True,
        # info={"edge": "LIMITS_WORKFLOWS_TO_QUERY"},
    )
    parent_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.workflow.id", ondelete="CASCADE"),
        index=True,
        # info={"edge": "IS_CHILD_OF_WORKFLOW"},
    )
    applicable_tabletype_id: Mapped[int] = mapped_column(
        ForeignKey("un0.tabletype.id", ondelete="CASCADE"),
        # info={"edge": "IS_WORKFLOW_FOR_tabletype"},
    )
    record_tabletype_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("un0.tabletype.id", ondelete="CASCADE"),
        # info={"edge": "HAS_workflowrecord_OF_tabletype"},
    )
    objectfunction_id: Mapped[Optional[str_26]] = mapped_column(
        ForeignKey("un0.objectfunction.id", ondelete="SET NULL"),
        index=True,
        # info={"edge": "IS_COMPLETED_BY_objectfunction"},
    )
    process_child_value: Mapped[bool] = mapped_column(
        server_default=text("true"),
        doc="The value returned by the Object Function that indicates that any child Workflows must be processed",
    )
    Index(
        "ix_workflow_applicable_tabletype_id",
        "applicable_tabletype_id",
        unique=True,
    )
    Index(
        "ix_workflowrecord_tabletype_id",
        "record_tabletype_id",
        unique=True,
    )

    # Relationships


class WorkflowEvent(Base, BaseMixin, RBACMixin):
    __tablename__ = "workflowevent"
    __table_args__ = {
        "schema": "un0",
        "comment": "Manually created or trigger created workflow activities",
    }

    id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.relatedobject.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        server_default=func.un0.insert_relatedobject("un0", "user"),
        doc="Primary Key",
        info={"edge": "HAS_ID"},
    )
    workflow_id: Mapped[int] = mapped_column(
        ForeignKey("un0.workflow.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "IS_TYPE_OF"},
    )
    date_due: Mapped[datetime.date] = mapped_column(doc="Date the workflow is due")
    workflow_object_id: Mapped[Optional[str_26]] = mapped_column(
        ForeignKey("un0.relatedobject.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "IS_EVENT_FOR"},
    )
    objectfunction_return_value: Mapped[Optional[bool]] = mapped_column(
        doc="Value returned by the Object Function to indicate the workflow is complete"
    )

    # Relationships


class WorkflowRecord(Base, BaseMixin, RBACMixin):
    __tablename__ = "workflowrecord"
    __table_args__ = {
        "schema": "un0",
        "comment": "Records of workflow events",
    }

    id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.relatedobject.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        server_default=func.un0.insert_relatedobject("un0", "user"),
        doc="Primary Key",
        info={"edge": "HAS_ID"},
    )
    workflowevent_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.workflowevent.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "IS_RECORD_OF"},
    )
    status: Mapped[WorkflowRecordStatus] = mapped_column(
        ENUM(
            WorkflowRecordStatus,
            name="workflowrecordstatus",
            create_type=True,
            schema="un0",
        ),
        default=WorkflowRecordStatus.OPEN,
        doc="Status of the workflow record",
    )
    state: Mapped[WorkflowRecordState] = mapped_column(
        ENUM(
            WorkflowRecordState,
            name="workflowrecordstate",
            create_type=True,
            schema="un0",
        ),
        default=WorkflowRecordState.PENDING,
        doc="State of the workflow record",
    )
    comment: Mapped[str] = mapped_column(
        doc="User defined or auto-generated comment on the workflow execution",
    )
    workflowrecord_id: Mapped[Optional[str_26]] = mapped_column(
        ForeignKey("un0.relatedobject.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "RECORDS_EXECUTION"},
    )
    # ForeignKeyConstraint(
    #    ["workflowrecord_id"],
    #    ["un0.relatedobject.id"],
    #    name="fk_workflowrecord_record_relatedobject_id",
    #    ondelete="CASCADE",
    # )

    # Relationships


class ObjectFunction(Base):
    __tablename__ = "objectfunction"
    __table_args__ = {
        "schema": "un0",
        "comment": "Functions that can be called by user-defined workflows and reports",
        "info": {"rls_policy": "superuser", "in_graph": False},
    }
    # Columns

    id: Mapped[int] = mapped_column(
        Identity(start=1, cycle=False),
        primary_key=True,
        index=True,
        doc="Primary Key",
    )
    label: Mapped[str] = mapped_column(doc="Label of the function")
    documentation: Mapped[Optional[str]] = mapped_column(
        doc="Documentation of the function"
    )
    name: Mapped[str] = mapped_column(doc="Name of the function")
    function_tabletype_id: Mapped[int] = mapped_column(
        ForeignKey("un0.tabletype.id", ondelete="CASCADE"),
        index=True,
        # info={"edge": "IS_OF_tabletype"},
    )
    # Relationships
