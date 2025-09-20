import os
from jinja2 import Template
from datetime import datetime

def generate_report(filename: str, paper_info:dict[str,str], 
                    errors: dict[str, list[str]], output_path: str):
    """
    使用模板生成 Markdown 格式的报告
    """
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    template = Template("""# 论文格式检查报告
                        
**论文标题**: {{ title }}

**作者**: {{ author }}

**学号**: {{ student_id }}

**生成时间**: {{ date }}

    {% if errors %}
## 错误详情
    {% for error_type, error_list in errors.items() %}
### {{ error_type }}
    {% for error in error_list %}
- {{ error }}
    {% endfor %}
    {% endfor %}

    {% else %}
论文格式检查通过，没有发现错误！
    {% endif %}
    """)

    report = template.render(
        errors=errors,
        title=paper_info.get("题目", "未提供"),
        author=paper_info.get("姓名", "未提供"),
        student_id=paper_info.get("学号", "未提供"),
        date=datetime.now().strftime("%Y年%m月%d日%H时%M分"),
    )
    with open(os.path.join(output_path, f"{filename}.md"), 'w', encoding='utf-8') as f:
        f.write(report)
    return report