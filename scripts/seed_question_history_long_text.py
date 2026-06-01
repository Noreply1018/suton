from __future__ import annotations

import json
import time

from app.db import connect


def main() -> None:
    suffix = time.time_ns()
    project_name = f"长题目历史项目 {suffix}"
    long_question = (
        "设函数 f 在闭区间 [0,1] 上连续，在开区间 (0,1) 内可导，且满足积分约束、端点约束和参数扰动条件；"
        "请证明存在唯一的 ξ 使得导数项、平均变化率、二阶差分估计以及给定长文本说明中全部附加条件同时成立。"
    )

    with connect() as conn:
        project = conn.execute("INSERT INTO projects (name, updated_at) VALUES (%s, now()) RETURNING id", (project_name,)).fetchone()
        question_ids: list[int] = []
        for index in range(20):
            row = conn.execute(
                """
                INSERT INTO questions (project_id, text, status, last_search_at, updated_at)
                VALUES (%s, %s, 'no_reliable_source', now() - (%s || ' minutes')::interval, now() - (%s || ' minutes')::interval)
                RETURNING id
                """,
                (project["id"], f"{long_question} 第 {index + 1:02d} 题。", index, index),
            ).fetchone()
            question_ids.append(row["id"])
        conn.commit()

    print(
        json.dumps(
            {
                "project_id": project["id"],
                "project_name": project_name,
                "question_ids": question_ids,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
