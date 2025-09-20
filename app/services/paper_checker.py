import os
import shutil
from fastapi import UploadFile
from pp4mat.config_converter import convert_config, Config, Args
from pp4mat.format_checker import check_format
from pp4mat.report import generate_report

UPLOAD_DIR = "./uploads"
REPORT_DIR = "./reports"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

def process_paper(file: UploadFile):
    assert file.filename is not None, "未提供文件"
    # 保存上传的文件
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # 加载配置并检测格式
    args = Args(
        config=os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'configs', "rules.yaml"),
        docx=file_path,
        debug=False,
        output=REPORT_DIR,
        log_dir=None
    )
    config = Config(args)
    convert_config(config.format_config)
    errors, cover_info = check_format(config)

    # 生成报告
    report = generate_report(filename, cover_info, errors, REPORT_DIR)
    return {"status": "fail", "report": report}