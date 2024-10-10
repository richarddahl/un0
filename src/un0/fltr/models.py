# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import datetime
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    UniqueConstraint,
    func,
    text,
    Identity,
)

from sqlalchemy.dialects.postgresql import (
    ENUM,
    ARRAY,
)
from sqlalchemy.orm import relationship, mapped_column, Mapped

from un0.fltr.enums import (  # type: ignore
    GraphType,
    EdgeDirection,
    Include,
    Match,
    Lookup,
    ColumnSecurity,
)
from un0.db import Base, BaseMixin, RBACMixin, str_26, str_255, decimal  # type: ignore
from un0.rltd.models import RelatedObject, TableType

"""
class FilterVertex(Base):
    __tablename__ = "filtervertex"
    __table_args__ = (
        {
            "schema": "un0",
            "info": {"rls_policy": False, "graph": False},
        },
    )

    # Columns
    id: Mapped[int] = mapped_column(
        Identity(start=1, cycle=False),
        primary_key=True,
        index=True,
        doc="Primary Key",
    )
    tabletype_id: Mapped[int] = mapped_column(
        ForeignKey("un0.tabletype.id", ondelete="CASCADE"),
        index=True,
        doc="The table type associated with the vertex.",
    )
    label: Mapped[str_255] = mapped_column(unique=True)


class FilterEdge(Base):
    __tablename__ = "filteredge"
    __table_args__ = (
        {
            "schema": "un0",
            "info": {"rls_policy": False, "graph": False},
        },
    )

    # Columns
    id: Mapped[int] = mapped_column(
        Identity(start=1, cycle=False),
        primary_key=True,
        index=True,
        doc="Primary Key",
    )
    label: Mapped[str_255] = mapped_column(unique=True)


class FilterVertexFilterEdge(Base):
    __tablename__ = "filtervertex_filteredge"
    __table_args__ = (
        Index("ix_vertex_id_edge_id", "vertex_id", "edge_id"),
        {
            "schema": "un0",
            "comment": "A vertex (FilterVertex) associated with an Edge.",
            "info": {"rls_policy": False, "graph": False},
        },
    )

    # Columns
    vertex_id: Mapped[int] = mapped_column(
        ForeignKey("un0.filtervertex.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        doc="A vertex associated with an edge.",
    )
    edge_id: Mapped[int] = mapped_column(
        ForeignKey("un0.filteredge.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        doc="An edge associated with a vertex.",
    )
    direction: Mapped[EdgeDirection] = mapped_column(
        ENUM(
            EdgeDirection,
            name="edgedirection",
            create_type=True,
            schema="un0",
        ),
        default=EdgeDirection.FROM,
    )


class FilterFieldFilterVertex(Base):
    __tablename__ = "filterfield_filtervertex"
    __table_args__ = (
        Index("ix_field_id_vertex_id", "field_id", "vertex_id"),
        {
            "schema": "un0",
            "comment": "A field (FilterField) associated with a Vertex.",
            "info": {"rls_policy": False, "graph": False},
        },
    )

    # Columns
    field_id: Mapped[int] = mapped_column(
        ForeignKey("un0.filterfield.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        doc="A field associated with a vertex.",
    )
    vertex_id: Mapped[int] = mapped_column(
        ForeignKey("un0.filtervertex.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        doc="A vertex associated with a field.",
    )


class FilterFieldFilterEdge(Base):
    __tablename__ = "filterfield_filteredge"
    __table_args__ = (
        Index("ix_field_id_edge_id", "field_id", "edge_id"),
        {
            "schema": "un0",
            "comment": "A field (FilterField) associated with an Edge.",
            "info": {"rls_policy": False, "graph": False},
        },
    )

    # Columns
    field_id: Mapped[int] = mapped_column(
        ForeignKey("un0.filterfield.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        doc="A field associated with a vertex.",
    )
    edge_id: Mapped[int] = mapped_column(
        ForeignKey("un0.filteredge.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        doc="An edge associated with a field.",
    )


"""


class FilterField(Base):
    __tablename__ = "filterfield"
    __table_args__ = (
        UniqueConstraint("accessor", "graph_type", name="uq_accessor_graph_type"),
        Index("ix_accessor_data_type", "accessor", "data_type"),
        {
            "schema": "un0",
            "comment": "Used to enable user-defined filtering using the graph vertices and edges.",
            "info": {"rls_policy": False, "graph": False},
        },
    )

    # Columns
    id: Mapped[int] = mapped_column(
        Identity(start=1, cycle=False),
        primary_key=True,
        index=True,
        doc="Primary Key",
    )
    name: Mapped[str_255] = mapped_column()
    accessor: Mapped[str_255] = mapped_column()
    data_type: Mapped[str_26] = mapped_column()
    graph_type: Mapped[ColumnSecurity] = mapped_column(
        ENUM(
            GraphType,
            name="graphtype",
            create_type=True,
            schema="un0",
        ),
        default=GraphType.PROPERTY,
    )
    lookups: Mapped[list[Lookup]] = mapped_column(
        ARRAY(
            ENUM(
                Lookup,
                name="lookup",
                create_type=True,
                schema="un0",
            )
        )
    )


class FilterFieldTableType(Base):
    __tablename__ = "filterfield_tabletype"
    __table_args__ = (
        Index("ix_filterfield_id_tabletype_id", "filterfield_id", "tabletype_id"),
        {
            "schema": "un0",
            "comment": "A FilterField associated with a TableType.",
            "info": {"rls_policy": False, "graph": False},
        },
    )

    # Columns
    filterfield_id: Mapped[int] = mapped_column(
        ForeignKey("un0.filterfield.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        doc="The filterfield associated with a tabletype.",
    )
    tabletype_id: Mapped[int] = mapped_column(
        ForeignKey("un0.tabletype.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        doc="The tabletype associated with a filterfield.",
    )


class FilterValue(Base, BaseMixin, RBACMixin):
    __tablename__ = "filtervalue"
    __table_args__ = (
        UniqueConstraint(
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
        Index(
            "ix_filtervalue__unique_together",
            "field_id",
            "lookup",
            "include",
            "match",
        ),
        CheckConstraint(
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
            name="ck_filtervalue",
        ),
        {
            "comment": "User definable values for use in queries.",
            "schema": "un0",
            "info": {"rls_policy": "default", "audit_type": "history"},
        },
    )

    # Columns
    id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.relatedobject.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        server_default=func.un0.insert_relatedobject("un0", "user"),
        doc="Primary Key",
        info={"edge": "HAS_ID"},
    )
    field_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.filterfield.id", ondelete="CASCADE"),
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
        ForeignKey("un0.relatedobject.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
        info={"edge": "HAS_OBJECT_VALUE"},
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        viewonly=True,
        doc="The tenant associated with the filter value.",
    )
    """
    fields: Mapped["Field"] = relationship(back_populates="filtervalues")
    # relatedobject: Mapped["RelatedObject"] = relationship(
    #    viewonly=True,
    #    back_populates="filtervalue",
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
            "info": {"rls_policy": "default", "audit_type": "history"},
        },
    )

    # Columns
    id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.relatedobject.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        server_default=func.un0.insert_relatedobject("un0", "user"),
        doc="Primary Key",
        info={"edge": "HAS_ID"},
    )
    name: Mapped[str_255] = mapped_column(doc="The name of the query.")
    queries_tabletype_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.tabletype.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "QUERIES_tabletype"},
    )
    show_results_with_object: Mapped[bool] = mapped_column(
        server_default=text("false"),
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
    query_filtervalue: Mapped[list["QueryFilterValue"]] = relationship(
        back_populates="query"
    )
    query_sub_query: Mapped[list["QuerySubquery"]] = relationship(
        back_populates="query"
    )
    """


class QueryFilterValue(Base, BaseMixin):
    __tablename__ = "query_filtervalue"
    __table_args__ = (
        Index("ix_query_id__filtervalue_id", "query_id", "filtervalue_id"),
        {
            "schema": "un0",
            "comment": "The filter values associated with a query.",
            "info": {"rls_policy": False, "vertex": False},
        },
    )

    # Columns
    query_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.query.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        info={"edge": "IS_QUERIED_THROUGH"},
    )
    filtervalue_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.filtervalue.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        info={"edge": "QUERIES_FILTERVALUE"},
    )

    # Relationships
    """
    query: Mapped[Query] = relationship(back_populates="query_filtervalue")
    filtervalue: Mapped[FilterValue] = relationship(
        back_populates="query_filtervalue"
    )
    """


class QuerySubquery(Base, BaseMixin):
    __tablename__ = "query_subquery"
    __table_args__ = (
        Index("ix_query_id__subquery_id", "query_id", "subquery_id"),
        {
            "schema": "un0",
            "comment": "The subqueries associated with a query",
            "info": {"rls_policy": False, "vertex": False},
        },
    )

    # Columns
    query_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.query.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        doc="The query the subquery is associated with.",
        info={"edge": "HAS_PARENT_QUERY"},
    )
    subquery_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.query.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        doc="The subquery associated with the query.",
        info={"edge": "HAS_SUBQUERY"},
    )

    # Relationships
    """
    query: Mapped["Query"] = relationship(back_populates="query_sub_query")
    subquery: Mapped["Query"] = relationship(back_populates="query_sub_query")
    """
