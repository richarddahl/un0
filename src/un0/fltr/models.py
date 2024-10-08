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
    Include,
    Match,
    Lookup,
    ColumnSecurity,
    selectlookups,
    numeric_lookups,
    string_lookups,
)
from un0.utilities import convert_snake_to_capital_word
from un0.db import Base, BaseMixin, RBACMixin, str_26, str_255, decimal  # type: ignore
from un0.rltd.models import RelatedObject, TableType


def create_fields(table, conn, db_name, superuser_id):
    print(f"Creating fields for {table.schema}.{table.name}")
    print(f"Superuser ID: {superuser_id}")
    for name, column in table.columns.items():
        if column.info.get("column_security") == "Secret":
            continue
        property_type = column.type.python_type.__name__
        if column.foreign_keys:
            lookups = selectlookups
        if property_type in ["int", "float", "Decimal", "datetime", "date", "time"]:
            lookups = numeric_lookups
        else:
            lookups = string_lookups
        property_label = column.info.get("edge", name.replace("_", " ").title())
        vertex_label = convert_snake_to_capital_word(table.name)
        conn.execute(
            text(
                f"""
                SET ROLE {db_name}_admin;
                INSERT INTO un0.field (
                    property_name,
                    property_label,
                    property_type,
                    includes,
                    matches,
                    lookups,
                    column_security
                )
                VALUES (
                    '{column.name}',
                    '{property_label}',
                    '{property_type}',
                    ARRAY['INCLUDE', 'EXCLUDE']::un0.include[],
                    ARRAY['AND', 'OR', 'NOT']::un0.match[],
                    ARRAY{lookups}::un0.lookup[],
                    'PUBLIC'
                )
                ON CONFLICT (property_name, property_type) DO NOTHING;

                INSERT INTO un0.vertex (
                    table_type_id,
                    vertex_label
                )
                SELECT
                    t.id,
                    '{vertex_label}'
                FROM un0.table_type t
                WHERE t.schema = '{table.schema}'
                AND t.name = '{table.name}'
                ON CONFLICT (table_type_id, vertex_label) DO NOTHING;

                INSERT INTO un0.property_vertex (
                    property_id,
                    vertex_id
                )
                SELECT
                    f.id,
                    v.id
                FROM un0.field f
                JOIN un0.vertex v
                ON f.property_name = '{column.name}'
                AND v.vertex_label = '{vertex_label}'
                ON CONFLICT (property_id, vertex_id) DO NOTHING
                """
            )
        )
        conn.commit()


class GraphVertex(Base):
    __tablename__ = "graph_vertex"
    __table_args__ = (
        UniqueConstraint("table_type_id", "vertex_label"),
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
    table_type_id: Mapped[int] = mapped_column(
        ForeignKey("un0.table_type.id", ondelete="CASCADE"),
        index=True,
        doc="The table type associated with the vertex.",
    )
    vertex_label: Mapped[str_255] = mapped_column()


class GraphEdge(Base):
    __tablename__ = "graph_edge"
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
    edge_label: Mapped[str_255] = mapped_column()


class GraphProperty(Base):
    __tablename__ = "graph_property"
    __table_args__ = (
        UniqueConstraint(
            "property_name", "property_type", name="uq_property_name_property_type"
        ),
        Index("ix_property_name_property_type", "property_name", "property_type"),
        {
            "schema": "un0",
            "comment": "Describes a property of a graph.",
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
    property_name: Mapped[str_255] = mapped_column()
    property_label: Mapped[str_255] = mapped_column()
    property_type: Mapped[str_26] = mapped_column()
    includes: Mapped[list[Include]] = mapped_column(
        ARRAY(
            ENUM(
                Include,
                name="include",
                create_type=True,
                schema="un0",
            )
        )
    )
    matches: Mapped[list[Match]] = mapped_column(
        ARRAY(
            ENUM(
                Match,
                name="match",
                create_type=True,
                schema="un0",
            )
        )
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
    column_security: Mapped[ColumnSecurity] = mapped_column(
        ENUM(
            ColumnSecurity,
            name="columsecurity",
            create_type=True,
            schema="un0",
        ),
        default=ColumnSecurity.PUBLIC,
    )


class PropertyVertex(Base):
    __tablename__ = "property_vertex"
    __table_args__ = (
        Index("ix_property_id_vertex_id", "property_id", "vertex_id"),
        {
            "schema": "un0",
            "comment": "A field (GraphProperty) associated with a vertex.",
            "info": {"rls_policy": False, "graph": False},
        },
    )

    # Columns
    property_id: Mapped[int] = mapped_column(
        ForeignKey("un0.graph_property.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        doc="A field associated with a vertex.",
    )
    vertex_id: Mapped[int] = mapped_column(
        ForeignKey("un0.graph_vertex.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        doc="A vertex associated with a field.",
    )


class FilterKey(Base, BaseMixin):
    __tablename__ = "filter_key"
    __table_args__ = {
        "schema": "un0",
        "comment": "Filter keys for filtering data",
        "info": {"rls_policy": False},
    }

    # Columns
    id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.related_object.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        server_default=func.un0.insert_related_object("un0", "user"),
        doc="Primary Key",
    )
    name: Mapped[str_255] = mapped_column(doc="Name")
    source_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.table_type.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    destination_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.table_type.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
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
        UniqueConstraint(
            "property_id",
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
            "property_id",
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
            name="ck_filter_value",
        ),
        {
            "comment": "User definable values for use in queries.",
            "schema": "un0",
            "info": {"rls_policy": "default", "audit_type": "history"},
        },
    )

    # Columns
    id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.related_object.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        server_default=func.un0.insert_related_object("un0", "user"),
        doc="Primary Key",
        info={"edge": "HAS_ID"},
    )
    property_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.graph_property.id", ondelete="CASCADE"),
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
        ForeignKey("un0.related_object.id", ondelete="CASCADE"),
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
            "info": {"rls_policy": "default", "audit_type": "history"},
        },
    )

    # Columns
    id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.related_object.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        server_default=func.un0.insert_related_object("un0", "user"),
        doc="Primary Key",
        info={"edge": "HAS_ID"},
    )
    name: Mapped[str_255] = mapped_column(doc="The name of the query.")
    queries_table_type_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.table_type.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "QUERIES_TABLE_TYPE"},
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
        ForeignKey("un0.filter_value.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        info={"edge": "QUERIES_FILTER_VALUE"},
    )

    # Relationships
    """
    query: Mapped[Query] = relationship(back_populates="query_filter_value")
    filter_value: Mapped[FilterValue] = relationship(
        back_populates="query_filter_value"
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
        info={"edge": "HAS_CHILD_QUERY"},
    )

    # Relationships
    """
    query: Mapped["Query"] = relationship(back_populates="query_sub_query")
    subquery: Mapped["Query"] = relationship(back_populates="query_sub_query")
    """
