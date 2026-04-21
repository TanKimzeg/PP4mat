from pathlib import Path
from jinja2 import Template
from datetime import datetime
from pp4mat.format_checker import FormatErrors

def generate_report(filename: str, paper_info:dict[str,str], 
                    errors: FormatErrors, output_dir: Path) -> str:
    """
    使用模板生成 Markdown 格式的报告
    """
    if not output_dir.exists():
        output_dir.mkdir(parents=True)

    has_errors = any(bool(v) for v in (errors or {}).values())

    template = Template("""# 论文格式检测结果
                        
**论文标题**: {{ title }}

**作者**: {{ author }}

**学号**: {{ student_id }}

**生成时间**: {{ date }}

{% if has_errors %}
## 错误详情
    {% for error_type, error_list in errors.items() %}
    {% if error_list %}
### {{ error_type }}
    {% for error in error_list %}
- {{ error }}
    {% endfor %}
    {% endif %}
    {% endfor %}

{% else %}
***格式检查通过，没有发现错误！***
{% endif %}
    """)

    report = template.render(
        errors=errors,
        has_errors=has_errors,
        title=paper_info.get("题目", "未提供"),
        author=paper_info.get("姓名", "未提供"),
        student_id=paper_info.get("学号", "未提供"),
        date=datetime.now().strftime("%Y年%m月%d日%H时%M分"),
    )
    with open(output_dir / f"{filename}.md", 'w', encoding='utf-8') as f:
        f.write(report)
    return report