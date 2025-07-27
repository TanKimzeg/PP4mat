import argparse
from pp4mat.config_converter import Config, convert_config, Args
from pp4mat.format_checker import check_format
from pp4mat.report import generate_report


def main() -> None:
    parser = argparse.ArgumentParser(description="论文格式检查工具")
    parser.add_argument('--docx', type=str, default=f'./paper.docx', help='论文文档路径')
    parser.add_argument('--config', type=str, default=f'./rules.yaml', help='配置文件路径，包含格式规则')
    parser.add_argument("--debug", action="store_true", help="启用调试模式以获取详细日志（默认：禁用）")
    parser.add_argument("--output", type=str, default="./reports", help="报告输出路径，默认为当前目录下的 report 文件夹")
    parser.add_argument("--log_dir", type=str, default="./error_logs", help="日志文件夹路径，默认为当前目录下的 error_logs 文件夹")
    
    args = parser.parse_args()

    # Load the format rules
    args = Args(
        docx=args.docx,
        config=args.config,
        debug=args.debug,
        log_dir=args.log_dir,
        output=args.output
    )
    config = Config(args)
    convert_config(config.format_config)


    # Check the format
    errors, cover_info = check_format(config)
    
    if errors:
        generate_report(cover_info, errors, config.output)
        print(f"报告已生成，请查看{config.output}目录下的 Markdown 文件。")
    else:
        print("格式检查通过，没有发现错误！")


if __name__ == "__main__":
    main()