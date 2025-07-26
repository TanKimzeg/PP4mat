import os
import argparse
from config_converter import Config
import logging
from config_converter import convert_config
from format_checker import check_format

def logger_config(debug_flag:bool=False) -> None:
    loggers = [
        'format_checker',
        'config_converter'
    ]
    if debug_flag:
        for logger_name in loggers:
            logging.getLogger(logger_name).setLevel(logging.DEBUG)

def main() -> None:
    parser = argparse.ArgumentParser(description="论文格式检查工具")
    parser.add_argument('--docx', type=str, default=f'./paper.docx', help='论文文档路径')
    parser.add_argument('--config', type=str, default=f'./rules.yaml', help='配置文件路径，包含格式规则')
    parser.add_argument("--debug", action="store_true", help="启用调试模式以获取详细日志（默认：禁用）")
    parser.add_argument("--output", type=str, default="./reports", help="报告输出路径，默认为当前目录下的 report 文件夹")
    
    args = parser.parse_args()
    logger_config(args.debug)

    # Load the format rules
    format_config = Config(args.config)
    convert_config(format_config)


    # Check the format
    # logging.info("Checking document format...")
    errors, cover_info = check_format(args.docx, format_config)
    
    if errors:
        generate_report(
            cover_info,
            errors, 
            args.output)
        print(f"报告已生成，请查看{args.output}目录下的 Markdown 文件。")
    else:
        print("格式检查通过，没有发现错误！")

def generate_report(paper_info:dict[str,str], errors: dict[str, list[str]], output_path: str) -> None:
    from jinja2 import Template
    from datetime import datetime
    """
    使用模板生成 Markdown 格式的报告
    """
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    template = Template("""
# 论文格式检查报告
                        
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
    {% endif %}
    """)

    report = template.render(
        errors=errors,
        title=paper_info.get("题目", "未提供"),
        author=paper_info.get("姓名", "未提供"),
        student_id=paper_info.get("学号", "未提供"),
        date=datetime.now().strftime("%Y年%m月%d日%H时%M分"),
    )
    with open(os.path.join(output_path, f"{paper_info.get("姓名","无名氏")}-{datetime.now().strftime("%H_%M_%S")}.md"), 'w', encoding='utf-8') as f:
        f.write(report)

if __name__ == "__main__":
    main()