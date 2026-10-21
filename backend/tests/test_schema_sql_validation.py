from __future__ import annotations

import unittest
import json

from app.querying.schema_sql_validation import schema_graph_sql_error
from app.querying.single_database_agent import SingleDatabaseAgent


def schema_graph(*, include_ads: bool = False, joins: list[dict] | None = None) -> dict:
    tables = [
        {
            "id": "short_video_ops.user_profiles",
            "name": "user_profiles",
        }
    ]
    fields = [
        {
            "table_id": "short_video_ops.user_profiles",
            "table_name": "user_profiles",
            "name": "region",
        }
    ]
    if include_ads:
        tables.append(
            {
                "id": "short_video_ops.ad_daily_stats",
                "name": "ad_daily_stats",
            }
        )
        fields.extend(
            [
                {
                    "table_id": "short_video_ops.ad_daily_stats",
                    "table_name": "ad_daily_stats",
                    "name": "spend",
                },
                {
                    "table_id": "short_video_ops.ad_daily_stats",
                    "table_name": "ad_daily_stats",
                    "name": "stat_date",
                },
            ]
        )
    return {"tables": tables, "fields": fields, "joins": joins or []}


class SchemaGraphSqlValidationTest(unittest.TestCase):
    def test_rejects_table_outside_current_schema_graph(self) -> None:
        error = schema_graph_sql_error(
            "SELECT SUM(ads.spend) FROM ad_daily_stats ads",
            schema_graph(),
        )

        self.assertIn("Schema图未提供表", error)
        self.assertIn("ad_daily_stats", error)

    def test_rejects_field_outside_current_schema_graph(self) -> None:
        error = schema_graph_sql_error(
            "SELECT up.user_id FROM user_profiles up",
            schema_graph(),
        )

        self.assertIn("Schema图未提供字段", error)
        self.assertIn("user_profiles.user_id", error)

    def test_rejects_join_outside_current_schema_graph(self) -> None:
        error = schema_graph_sql_error(
            "SELECT up.region, SUM(ads.spend) "
            "FROM ad_daily_stats ads "
            "JOIN user_profiles up ON ads.user_id = up.user_id "
            "GROUP BY up.region",
            schema_graph(include_ads=True),
        )

        self.assertIn("Schema图未提供关联", error)
        self.assertIn("ad_daily_stats.user_id", error)
        self.assertIn("user_profiles.user_id", error)

    def test_accepts_fields_from_a_single_schema_graph_table(self) -> None:
        error = schema_graph_sql_error(
            "SELECT up.region FROM user_profiles up GROUP BY up.region",
            schema_graph(),
        )

        self.assertEqual("", error)

    def test_accepts_join_explicitly_provided_by_schema_graph(self) -> None:
        graph = schema_graph(
            include_ads=True,
            joins=[
                {
                    "left_table_name": "ad_daily_stats",
                    "left_field": "ad_campaign_id",
                    "right_table_name": "user_profiles",
                    "right_field": "user_id",
                }
            ],
        )
        graph["fields"].extend(
            [
                {
                    "table_id": "short_video_ops.ad_daily_stats",
                    "table_name": "ad_daily_stats",
                    "name": "ad_campaign_id",
                },
                {
                    "table_id": "short_video_ops.user_profiles",
                    "table_name": "user_profiles",
                    "name": "user_id",
                },
            ]
        )

        error = schema_graph_sql_error(
            "SELECT up.region, SUM(ads.spend) "
            "FROM ad_daily_stats ads "
            "JOIN user_profiles up ON ads.ad_campaign_id = up.user_id "
            "GROUP BY up.region",
            graph,
        )

        self.assertEqual("", error)


class SequencedModel:
    def __init__(self, decisions: list[dict]) -> None:
        self.decisions = iter(decisions)
        self.payloads: list[dict] = []

    def chat_json(self, _system: str, user: str) -> dict:
        self.payloads.append(json.loads(user))
        return next(self.decisions)


class SingleDatabaseAgentSchemaValidationTest(unittest.TestCase):
    def test_invalid_schema_sql_is_returned_to_model_before_tool_execution(self) -> None:
        model = SequencedModel(
            [
                {
                    "action": "call_tool",
                    "tool_name": "query_short_video_ops",
                    "arguments": {
                        "sql": "SELECT SUM(ads.spend) FROM ad_daily_stats ads"
                    },
                },
                {
                    "action": "clarify",
                    "clarification": {
                        "parameter": "metric",
                        "question": "当前Schema没有销售额，是否改查其他指标？",
                        "options": [{"id": "spend"}, {"id": "cancel"}],
                    },
                },
            ]
        )
        agent = object.__new__(SingleDatabaseAgent)
        agent.model_client = model
        agent.skill = type(
            "Skill",
            (),
            {"output_actions": ("call_tool", "clarify")},
        )()

        decision = agent._validated_decision(
            "system",
            {
                "query": "查询本月各地区销售额",
                "schema_graph": schema_graph(),
                "retrieval": {"selected_fields": []},
            },
            {"query_short_video_ops"},
        )

        self.assertEqual("clarify", decision["action"])
        self.assertIn("Schema图未提供表", model.payloads[1]["output_validation_error"])
        self.assertIn("ad_daily_stats", model.payloads[1]["output_validation_error"])
        self.assertIn("不得用其他指标替代", model.payloads[1]["output_validation_instruction"])


if __name__ == "__main__":
    unittest.main()
