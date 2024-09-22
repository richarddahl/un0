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

from un0.fltr.enums import (  # type: ignore
    Include,
    Match,
    Lookup,
)
from un0.db import Base, BaseMixin, RBACMixin, str_26, str_255, decimal  # type: ignore
from un0.rltd.models import RelatedObject, TableType


class FilterKey(Base, BaseMixin):
    __tablename__ = "filter_key"
    __table_args__ = {
        "schema": "un0",
        "comment": "Filter keys for filtering data",
        "info": {"rls_policy": "superuser"},
    }

    # Columns
    name: Mapped[str_255] = mapped_column(doc="Name")
    source_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.table_type.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        info={"edge": "IS_OF_SOURCE"},
    )
    destination_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.table_type.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        info={"edge": "IS_OF_DESTINATION"},
    )
    filter_string: Mapped[str] = mapped_column(doc="Filter String")
    value_filter_string: Mapped[str] = mapped_column(doc="Value Filter String")
    include_in_table_filters: Mapped[bool] = mapped_column(
        default=True, doc="Include in Table Filters"
    )
    negate_filter: Mapped[bool] = mapped_column(default=False, doc="Negate Filter")
    data_type: Mapped[str_26] = mapped_column(doc="Data Type")
    choices: Mapped[Optional[str_26]] = mapped_column(doc="Choices")
    order_string: Mapped[Optional[str_255]] = mapped_column(
        default="id", doc="Order String"
    )
    object_representation: Mapped[str_26] = mapped_column(
        default="__str__", doc="Object Representation"
    )

    # Relationships
    """
    source: Mapped["TableType"] = relationship(
        back_populates="source_filter_keys", foreign_keys=[source_id]
    )
    destination: Mapped["TableType"] = relationship(
        back_populates="destination_filter_keys", foreign_keys=[destination_id]
    )
    """


class FilterValue(Base, BaseMixin, RBACMixin):
    __tablename__ = "filter_value"
    __table_args__ = (
        sa.UniqueConstraint(
            "field_id",
            "lookup",
            "include",
            "match",
            "bigint_value",
            "boolean_value",
            "date_value",
            "decimal_value",
            "object_value_id",
            "string_value",
            "text_value",
            "time_value",
            "timestamp_value",
            postgresql_nulls_not_distinct=True,
        ),
        sa.Index(
            "ix_filtervalue__unique_together",
            "field_id",
            "lookup",
            "include",
            "match",
        ),
        sa.CheckConstraint(
            """
                bigint_value IS NOT NULL
                OR boolean_value IS NOT NULL
                OR date_value IS NOT NULL
                OR decimal_value IS NOT NULL
                OR object_value_id IS NOT NULL
                OR string_value IS NOT NULL
                OR text_value IS NOT NULL
                OR time_value IS NOT NULL
                OR timestamp_value IS NOT NULL
            """,
            name="ck_filter_value",
        ),
        {
            "comment": "User definable values for use in queries.",
            "schema": "un0",
        },
    )

    # Columns
    field_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.field.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        info={"edge": "FILTERS_FIELD"},
    )
    lookup: Mapped[Lookup] = mapped_column(
        ENUM(
            Lookup,
            name="lookup",
            create_type=True,
            schema="un0",
        ),
        insert_default=Lookup.EQUAL,
    )
    include: Mapped[Include] = mapped_column(
        ENUM(
            Include,
            name="include",
            create_type=True,
            schema="un0",
        ),
        insert_default=Include.INCLUDE,
    )
    match: Mapped[Match] = mapped_column(
        ENUM(Match, name="match", create_type=True, schema="un0"),
        insert_default=Match.AND,
    )
    bigint_value: Mapped[Optional[int]] = mapped_column()
    boolean_value: Mapped[Optional[bool]] = mapped_column()
    date_value: Mapped[Optional[datetime.date]] = mapped_column()
    decimal_value: Mapped[Optional[decimal]] = mapped_column()
    text_value: Mapped[Optional[str]] = mapped_column()
    time_value: Mapped[Optional[datetime.time]] = mapped_column()
    timestamp_value: Mapped[Optional[datetime.datetime]] = mapped_column()
    string_value: Mapped[Optional[str_255]] = mapped_column()
    object_value_id: Mapped[Optional[str_26]] = mapped_column(
        sa.ForeignKey("un0.related_object.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
        info={"edge": "HAS_OBJECT_VALUE"},
    )

    # Relationships
    customer: Mapped["Customer"] = relationship(
        viewonly=True,
        doc="The customer associated with the filter value.",
    )
    """
    fields: Mapped["Field"] = relationship(back_populates="filter_values")
    # related_object: Mapped["RelatedObject"] = relationship(
    #    viewonly=True,
    #    back_populates="filter_value",
    #    foreign_keys=[object_value_id],
    #    doc="Object value",
    # )
    object_value: Mapped["RelatedObject"] = relationship(
        back_populates="filter_object_values",
        foreign_keys=[object_value_id],
        doc="Object value",
    )
    """


class Query(Base, BaseMixin, RBACMixin):
    __tablename__ = "query"
    __table_args__ = (
        {
            "comment": "User definable queries",
            "schema": "un0",
        },
    )

    # Columns
    name: Mapped[str_255] = mapped_column(doc="The name of the query.")
    table_type_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.table_type.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "QUERIES_TABLE_TYPE"},
    )
    show_results_with_object: Mapped[bool] = mapped_column(
        server_default=sa.text("false"),
        doc="Indicates if the results of the query should be returned with objects from the queries table type.",
    )
    include_values: Mapped[Include] = mapped_column(
        ENUM(
            Include,
            name="include",
            create_type=True,
            schema="un0",
        ),
        insert_default=Include.INCLUDE,
        doc="Indicate if the query should return records including or excluding the queries results.",
    )
    match_values: Mapped[Match] = mapped_column(
        ENUM(Match, name="match", create_type=True, schema="un0"),
        insert_default=Match.AND,
        doc="Indicate if the query should return records matching all or any of the filter values.",
    )
    include_subqueries: Mapped[Include] = mapped_column(
        ENUM(
            Include,
            name="include",
            create_type=True,
            schema="un0",
        ),
        insert_default=Include.INCLUDE,
        doc="Indicate if the query should return records including or excluding the subqueries results.",
    )
    match_subqueries: Mapped[Match] = mapped_column(
        ENUM(Match, name="match", create_type=True, schema="un0"),
        insert_default=Match.AND,
        doc="Indicate if the query should return records matching all or any of the subquery values.",
    )

    # Relationships
    """
    query_filter_value: Mapped[list["QueryFilterValue"]] = relationship(
        back_populates="query"
    )
    query_sub_query: Mapped[list["QuerySubquery"]] = relationship(
        back_populates="query"
    )
    """


class QueryFilterValue(Base, BaseMixin):
    __tablename__ = "query_filter_value"
    __table_args__ = (
        sa.Index("ix_query_id__filtervalue_id", "query_id", "filtervalue_id"),
        {
            "schema": "un0",
            "comment": "The filter values associated with a query.",
            "info": {"edge": "QUERIES_FILTER", "rls_policy": "none"},
        },
    )

    # Columns
    query_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.query.id", ondelete="CASCADE"), index=True, primary_key=True
    )
    filtervalue_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.filter_value.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
    )

    # Relationships
    """
    query: Mapped[Query] = relationship(back_populates="query_filter_value")
    filter_value: Mapped[FilterValue] = relationship(
        back_populates="query_filter_value"
    )
    """


class QuerySubquery(Base, BaseMixin):
    __tablename__ = "query_sub_query"
    __table_args__ = (
        sa.Index("ix_query_id__subquery_id", "query_id", "subquery_id"),
        {
            "schema": "un0",
            "comment": "The subqueries associated with a query",
            "info": {"edge": "QUERIES_SUBQUERY", "rls_policy": "none"},
        },
    )

    # Columns
    query_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.query.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        doc="The query the subquery is associated with.",
    )
    subquery_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.query.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        doc="The subquery associated with the query.",
    )

    # Relationships
    """
    query: Mapped["Query"] = relationship(back_populates="query_sub_query")
    subquery: Mapped["Query"] = relationship(back_populates="query_sub_query")
    """
