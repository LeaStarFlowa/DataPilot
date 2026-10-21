from __future__ import annotations

from typing import Any

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError


def schema_graph_sql_error(sql: str, schema_graph: dict[str, Any]) -> str:
    """Return why SQL exceeds the retrieved Schema graph, or an empty string."""
    try:
        statements = [item for item in sqlglot.parse(sql, read="duckdb") if item]
    except ParseError as exc:
        return f"SQL无法解析：{exc}"
    if len(statements) != 1:
        return "一次只能校验一条SQL"

    statement = statements[0]
    cte_names = {cte.alias_or_name for cte in statement.find_all(exp.CTE)}
    allowed_tables = {
        str(table.get("name") or table.get("id") or "").split(".")[-1]
        for table in schema_graph.get("tables", [])
    }
    allowed_fields: dict[str, set[str]] = {table: set() for table in allowed_tables}
    for field in schema_graph.get("fields", []):
        table_name = str(field.get("table_name") or field.get("table_id") or "").split(".")[-1]
        field_name = str(field.get("name") or "")
        if table_name and field_name:
            allowed_fields.setdefault(table_name, set()).add(field_name)

    alias_to_table: dict[str, str] = {}
    referenced_tables: list[str] = []
    for table in statement.find_all(exp.Table):
        if table.name in cte_names:
            continue
        table_name = table.name
        referenced_tables.append(table_name)
        alias_to_table[table.alias_or_name] = table_name
        alias_to_table.setdefault(table_name, table_name)

    unknown_tables = sorted(set(referenced_tables) - allowed_tables)
    if unknown_tables:
        return "SQL引用了Schema图未提供表：" + "、".join(unknown_tables)

    allowed_joins = {
        frozenset(
            (
                (
                    str(join.get("left_table_name") or join.get("left_table") or "").split(".")[-1],
                    str(join.get("left_field") or ""),
                ),
                (
                    str(join.get("right_table_name") or join.get("right_table") or "").split(".")[-1],
                    str(join.get("right_field") or ""),
                ),
            )
        )
        for join in schema_graph.get("joins", [])
    }
    for equality in statement.find_all(exp.EQ):
        left = equality.this
        right = equality.expression
        if not isinstance(left, exp.Column) or not isinstance(right, exp.Column):
            continue
        left_table = alias_to_table.get(left.table)
        right_table = alias_to_table.get(right.table)
        if not left_table or not right_table or left_table == right_table:
            continue
        relation = frozenset(
            ((left_table, left.name), (right_table, right.name))
        )
        if relation not in allowed_joins:
            return (
                "SQL使用了Schema图未提供关联："
                f"{left_table}.{left.name} = {right_table}.{right.name}"
            )

    projection_aliases = {
        projection.alias
        for select in statement.find_all(exp.Select)
        for projection in select.expressions
        if projection.alias
    }
    unknown_fields: list[str] = []
    physical_tables = set(referenced_tables)
    for column in statement.find_all(exp.Column):
        if column.table in cte_names or (not column.table and column.name in projection_aliases):
            continue
        table_name = alias_to_table.get(column.table) if column.table else None
        if table_name is None and len(physical_tables) == 1:
            table_name = next(iter(physical_tables))
        if table_name and column.name not in allowed_fields.get(table_name, set()):
            unknown_fields.append(f"{table_name}.{column.name}")
    if unknown_fields:
        return "SQL引用了Schema图未提供字段：" + "、".join(dict.fromkeys(unknown_fields))

    return ""
