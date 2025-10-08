import os
import shutil
from hashlib import md5
from functools import lru_cache
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
    
    # 重命名并检查文件是否存在
    filename = f"{md5(file.file.read()).hexdigest()}.docx"
    file.file.seek(0)  # 重置文件指针位置
    file_path = os.path.join(UPLOAD_DIR, filename)
    report_path = os.path.join(REPORT_DIR, f"{filename}.md")
    if os.path.exists(file_path) and os.path.exists(report_path):
        report = open(report_path, 'r', encoding='utf-8').read()
        return {"status": "fail", "report": report}
    # 保存上传的文件
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # 加载配置并检测格式
    config = get_partial_config()
    config.docx = file_path
    errors, cover_info = check_format(config)

    # 生成报告
    report = generate_report(filename, cover_info, errors, REPORT_DIR)
    return {"status": "fail", "report": report}

@lru_cache(maxsize=1)
def get_partial_config() -> Config:
    args = Args(
        config=os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'configs', "rules.yaml"),
        docx="",
        debug=False,
        output=REPORT_DIR,
        log_dir=None
    )
    config = Config(args)
    convert_config(config.format_config)
    return config