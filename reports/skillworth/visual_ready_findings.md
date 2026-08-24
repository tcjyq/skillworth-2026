# SkillWorth Visual-ready Findings

Snapshot：`freehire_china_tech_2026_08`。口径：2026-08 当前可观察的开放岗位快照，不代表所有岗位均发布于 2026 年。

## 1. 从主榜排除的技能

- AI：AI 是宽泛领域概念，无法对应单一、可验证的下一步学习目标。（404 jobs）
- Optimization：Optimization 含义过宽，无法对应单一学习目标。（234 jobs）
- Agile：Agile 是一般工作方法，不是具体技术学习资产。（107 jobs）
- PowerPoint：一般生产力工具不参与具体技术学习主榜。（67 jobs）
- Word：一般生产力工具不参与具体技术学习主榜。（37 jobs）
- Scrum：Scrum 是一般工作方法，不是具体技术学习资产。（21 jobs）
- Confluence：Confluence 是一般协作工具，不进入技术技能主榜。（15 jobs）
- Microsoft 365：一般生产力工具不参与具体技术学习主榜。（5 jobs）
- User Research：用户研究属于产品专业方法，不进入技术技能主榜。（5 jobs）
- Google Sheets：一般生产力工具不参与具体技术学习主榜。（1 jobs）

## 2. 主榜资格规模

main=113，secondary=15，excluded=10。

## 3. 排名稳健性

robust=25，moderate=32，sensitive=81。Ranking Robustness 不等同于统计置信度。

## 4. 最稳健的高技值候选

Python（23.82）, SQL（22.28）, Git（17.68）, Docker（15.84）, Power BI（15.25）, AWS（12.97）, Java（11.78）, Kubernetes（11.30）, MySQL（11.07）, React（11.06）, Apache Spark（10.81）, PostgreSQL（10.01）, Terraform（9.49）, JavaScript（9.18）, Node.js（8.84）

## 5. 市场价值高但学习投入高

Python（160h）, AWS（220h）, Azure（220h）, Java（220h）, Kubernetes（220h）, Google Cloud（220h）, C++（260h）, Linux（180h）, Apache Spark（190h）, PyTorch（180h）

## 6. 学习成本低但市场价值一般

XML（30h）, Jupyter（35h）, Vite（45h）, Postman（45h）, SQLite（50h）, Tailwind CSS（55h）, JUnit（55h）, pytest（55h）, GitLab CI（70h）, Matplotlib（70h）

## 7. Demand 高但不适合主榜

AI（404 jobs）, Optimization（234 jobs）, Agile（107 jobs）, PowerPoint（67 jobs）, Word（37 jobs）, Scrum（21 jobs）, Confluence（15 jobs）, Microsoft 365（5 jobs）, User Research（5 jobs）, Google Sheets（1 jobs）

## 8. 90 / 180 / 365 day 差异

- 90d: jobs=858, companies=293, skills=134, status=available
- 180d: jobs=992, companies=313, skills=134, status=available
- 365d: jobs=1036, companies=324, skills=136, status=available
- all_active: jobs=1134, companies=339, skills=138, status=available

各窗口 Top 10 high SkillWorth candidates：

- 90d: Python, SQL, Git, Docker, Power BI, AWS, RAG, Tableau, Bash, Java
- 180d: Python, SQL, Git, Docker, Power BI, AWS, Tableau, RAG, Java, MySQL
- 365d: Python, SQL, Git, Docker, Power BI, AWS, Java, Tableau, MySQL, RAG
- all_active: Python, SQL, Git, Docker, Power BI, AWS, Tableau, Azure, Bash, Java

## 9. 首页默认窗口

建议 `180d`。选择规则为最短且 available、同时覆盖至少 80% all-active 岗位的窗口。

## 10. 是否适合公开 SkillWorth Matrix

适合进入受限的真实数据可视化重构，但必须持续显示单来源、Low/Medium Confidence、Salary unavailable 与 Trend unavailable；当前不构成生产级劳动力市场结论。

## Market Themes

- AI: jobs=456, coverage=40.21%, companies=175, roles=18
- Machine Learning: jobs=262, coverage=23.10%, companies=105, roles=16
- Optimization: jobs=234, coverage=20.63%, companies=113, roles=18
- Data Warehousing: jobs=104, coverage=9.17%, companies=56, roles=14
- Computer Vision: jobs=33, coverage=2.91%, companies=15, roles=7
- Serverless: jobs=6, coverage=0.53%, companies=4, roles=3
