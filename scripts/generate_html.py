#!/usr/bin/env python3
"""HTML 报告生成器"""

import json
from datetime import datetime
from pathlib import Path
from jinja2 import Template

TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ date }} AI 资讯日报</title>
    <style>
        :root { --primary: #6366f1; --bg: #0f172a; --card: #1e293b; --text: #e2e8f0; --muted: #94a3b8; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header { background: linear-gradient(135deg, #6366f1, #8b5cf6); padding: 40px 20px; text-align: center; border-radius: 16px; margin-bottom: 30px; }
        h1 { font-size: 2em; margin-bottom: 10px; }
        .summary { background: var(--card); border-radius: 12px; padding: 25px; margin-bottom: 30px; border-left: 4px solid var(--primary); }
        .summary h2 { color: var(--primary); margin-bottom: 15px; }
        .trends { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 15px; }
        .trend { background: rgba(99,102,241,0.2); color: var(--primary); padding: 6px 14px; border-radius: 20px; font-size: 0.9em; }
        .section { margin-bottom: 40px; }
        .section-title { font-size: 1.5em; margin-bottom: 20px; padding-left: 15px; border-left: 4px solid var(--primary); }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }
        .card { background: var(--card); border-radius: 10px; padding: 20px; border: 1px solid #334155; transition: all 0.2s; cursor: pointer; }
        .card:hover { transform: translateY(-3px); border-color: var(--primary); }
        .card-title { font-size: 1.1em; font-weight: 600; margin-bottom: 10px; }
        .card-content { color: var(--muted); font-size: 0.95em; margin-bottom: 15px; }
        .card-meta { display: flex; justify-content: space-between; font-size: 0.85em; color: var(--muted); padding-top: 15px; border-top: 1px solid #334155; }
        .source { color: var(--primary); font-weight: 500; }
        footer { text-align: center; padding: 40px 20px; color: var(--muted); }
        a { color: var(--primary); text-decoration: none; }
        @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } h1 { font-size: 1.5em; } }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🤖 AI 资讯日报</h1>
            <div>{{ date }}</div>
        </header>

        {% if analysis %}
        <div class="summary" style="{% if '⚠️' in analysis.summary or 'AI 处理失败' in analysis.summary %}background: #7f1d1d; border-color: #ef4444;{% endif %}">
            <h2>{% if '⚠️' in analysis.summary %}⚠️ 错误信息{% else %}📝 今日摘要{% endif %}</h2>
            <p style="{% if '⚠️' in analysis.summary %}color: #fca5a5; font-weight: bold;{% endif %}">{{ analysis.summary }}</p>
            {% if analysis.trends %}
            <div class="trends">
                {% for t in analysis.trends %}<span class="trend">{{ t }}</span>{% endfor %}
            </div>
            {% endif %}
        </div>
        {% endif %}

        {% for category, items in categories.items() %}
        {% if items %}
        <div class="section">
            <h2 class="section-title">{{ category }}</h2>
            <div class="grid">
                {% for item in items %}
                <div class="card" onclick="window.open('{{ item.链接 }}', '_blank')">
                    <div class="card-title">{{ item.标题 }}</div>
                    {% if item.内容 %}<div class="card-content">{{ item.内容[:150] }}...</div>{% endif %}
                    {% if item.get('额外') %}<div class="card-content" style="color: #fbbf24;">{{ item.额外 }}</div>{% endif %}
                    <div class="card-meta">
                        <span class="source">{{ item.来源 }}</span>
                        <span>{{ item.日期[:10] if item.日期 else '' }}</span>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
        {% endfor %}

        <footer>
            <p>🤖 由 GitHub Actions + Claude AI 自动生成</p>
            <p>更新时间：{{ update_time }}</p>
        </footer>
    </div>
</body>
</html>"""


def main():
    data_dir = Path("data")
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)
    
    latest_file = data_dir / "latest.json"
    if not latest_file.exists():
        print("❌ 没有数据文件")
        return
    
    with open(latest_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    template = Template(TEMPLATE)
    html = template.render(
        date=data.get("date", datetime.now().strftime("%Y-%m-%d")),
        categories=data.get("categories", {}),
        analysis=data.get("analysis", {}),
        update_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
    # 保存
    (docs_dir / "index.html").write_text(html, encoding="utf-8")
    (docs_dir / f"digest_{data.get('date', 'latest')}.html").write_text(html, encoding="utf-8")
    
    print(f"✅ HTML 生成完成: docs/index.html")


if __name__ == "__main__":
    main()
