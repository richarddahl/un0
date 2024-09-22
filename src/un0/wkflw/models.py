# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import datetime

from typing import Optional

import sqlalchemy as sa
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
from un0.db import Base, BaseMixin, RBACMixin, RelatedObject, TableType, str_26, str_255  # type: ignore
from un0.fltr.models import Query


class Workflow(Base, BaseMixin):
    __tablename__ = "workflow"
    __table_args__ = {
        "schema": "un0",
        "comment": "User-defined workflows",
        "info": {"rls_policy": "superuser"},
    }

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
        server_default=sa.text("0"), doc="Repeat every x days"
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
        server_default=sa.text("7"), doc="Due within x days"
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
        server_default=sa.text("false"),
        doc="Indicates if the workflow should be run automatically",
    )
    record_required: Mapped[bool] = mapped_column(
        server_default=sa.text("false"), doc="Indicats if a Workflow Record is required"
    )
    limiting_query_id: Mapped[Optional[str_26]] = mapped_column(
        sa.ForeignKey(
            "un0.query.id",
            ondelete="SET NULL",
            name="fk_workflow_query_id",
        ),
        index=True,
        info={"edge": "LIMITS_WORKFLOWS_TO_QUERY"},
    )
    parent_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.workflow.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "IS_CHILD_OF_WORKFLOW"},
    )
    applicable_table_type_id: Mapped[int] = mapped_column(
        sa.ForeignKey("un0.table_type.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "IS_WORKFLOW_FOR_TABLE_TYPE"},
    )
    record_table_type_id: Mapped[Optional[int]] = mapped_column(
        sa.ForeignKey("un0.table_type.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "HAS_WORKFLOW_RECORD_OF_TABLE_TYPE"},
    )
    objectfunction_id: Mapped[Optional[str_26]] = mapped_column(
        sa.ForeignKey("un0.object_function.id", ondelete="SET NULL"),
        index=True,
        info={"edge": "IS_COMPLETED_BY_OBJECT_FUNCTION"},
    )
    process_child_value: Mapped[bool] = mapped_column(
        server_default=sa.text("true"),
        doc="The value returned by the Object Function that indicates that any child Workflows must be processed",
    )

    # Relationships
    """
    limiting_query: Mapped["Query"] = relationship(
        back_populates="workflow",
        foreign_keys=[limiting_query_id],
        doc="Query that limits the applicability of the workflow",
    )
    parent: Mapped["Workflow"] = relationship(
        back_populates="children",
        remote_side=[id],
        doc="Parent Workflow",
    )
    children: Mapped[list["Workflow"]] = relationship(
        back_populates="parent",
        foreign_keys=[parent_id],
        doc="Child Workflows",
    )
    applicable_table_type: Mapped[TableType] = relationship(
        back_populates="workflow",
        foreign_keys=[applicable_table_type_id],
        doc="Type of Table subject to the workflow",
    )
    record_table_type: Mapped[TableType] = relationship(
        back_populates="workflow",
        foreign_keys=[record_table_type_id],
        doc="Type of Table object that records the workflow's execution",
    )
    object_function: Mapped["ObjectFunction"] = relationship(
        back_populates="workflow",
        doc="Function called by auto run workflows to determine if the workflow is complete",
    )
    """


class WorkflowEvent(Base, BaseMixin, RBACMixin):
    __tablename__ = "workflow_event"
    __table_args__ = {
        "schema": "un0",
        "comment": "Manually created or trigger created workflow activities",
    }

    workflow_id: Mapped[int] = mapped_column(
        sa.ForeignKey("un0.workflow.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "IS_TYPE_OF"},
    )
    date_due: Mapped[datetime.date] = mapped_column(doc="Date the workflow is due")
    workflow_object_id: Mapped[Optional[str_26]] = mapped_column(
        sa.ForeignKey("un0.related_object.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "IS_EVENT_FOR"},
    )
    object_function_return_value: Mapped[Optional[bool]] = mapped_column(
        doc="Value returned by the Object Function to indicate the workflow is complete"
    )

    # Relationships
    """
    workflow: Mapped[Workflow] = relationship(
        back_populates="workflow_event",
        foreign_keys=[workflow_id],
        doc="Workflow with which the event is associated",
    )
    workflow_object: Mapped[RelatedObject] = relationship(
        back_populates="workflow_event",
        foreign_keys=[object_id],
        doc="Object for which the workflow is completed",
    )
    """


class WorkflowRecord(Base, BaseMixin, RBACMixin):
    __tablename__ = "workflow_record"
    __table_args__ = {
        "schema": "un0",
        "comment": "Records of workflow events",
    }

    workflow_event_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.workflow_event.id", ondelete="CASCADE"),
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
    workflow_record_id: Mapped[Optional[str_26]] = mapped_column(
        sa.ForeignKey("un0.related_object.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "RECORDS_EXECUTION"},
    )

    # Relationships
    """
    workflow_event: Mapped[WorkflowEvent] = relationship(
        back_populates="workflow_record",
        foreign_keys=[workflow_event_id],
        doc="Workflow Event that triggered the record",
    )
    record: Mapped[RelatedObject] = relationship(
        back_populates="workflow_record",
        foreign_keys=[record_id],
        doc="Record of the workflows execution",
    )
    """


class ObjectFunction(Base, BaseMixin):
    __tablename__ = "object_function"
    __table_args__ = {
        "schema": "un0",
        "comment": "Functions that can be called by user-defined workflows and reports",
        "info": {"rls_policy": "superuser"},
    }
    # Columns

    label: Mapped[str] = mapped_column(doc="Label of the function")
    documentation: Mapped[Optional[str]] = mapped_column(
        doc="Documentation of the function"
    )
    name: Mapped[str] = mapped_column(doc="Name of the function")
    table_type_id: Mapped[int] = mapped_column(
        sa.ForeignKey("un0.table_type.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "IS_OF_TABLE_TYPE"},
    )
    # Relationships
    """
    table_type: Mapped[TableType] = relationship(
        back_populates="object_function", doc="Table Type of the function"
    )
    """
