# 短视频运营问数评测

当前评测集包含 430 条用例，覆盖用户增长、渠道投放和内容运营；其中 49 条标记为经典冒烟用例。

## 指标

- 字段级 Schema 召回率：正确召回字段数 / 标准字段数
- 字段级 Schema 准确率：正确召回字段数 / 实际召回字段数
- SQL 执行成功率：成功执行 SQL 数 / 测试用例数
- 查询结果正确率：模型 SQL 与标准 SQL 的执行结果一致数 / 测试用例数
- SQL 执行时间：DuckDB 执行层平均耗时与 P95 耗时

结果比较允许等价 SQL；未要求排序时忽略行列顺序，明确要求 Top N 或排序时校验顺序和数量。

## 运行

在 `backend` 目录执行：

```powershell
# 验证全部标准 SQL，不调用模型
.\.venv\Scripts\python.exe -m evaluation.run_benchmark --mode gold --scope all

# 运行 49 条经典冒烟用例，会调用模型服务
.\.venv\Scripts\python.exe -u -m evaluation.run_benchmark --mode live --scope classic

# 运行全部 430 条用例，会调用模型服务
.\.venv\Scripts\python.exe -u -m evaluation.run_benchmark --mode live --scope all
```

已完成的基线报告保存在 `evaluation/results`，包含 JSON、CSV 和 Markdown 三种格式。运行 live 评测会产生接口调用费用。
