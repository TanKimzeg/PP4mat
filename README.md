# 论文格式检测工具

## 功能

- [x] 论文中包含毕业设计封面、中英文摘要、关键词、目录、正文、参考文献等各部分完整，总字数不低于1万字
- [x] 参考文献总数不少于15项，其中英文不少于2项
- [x] 参考文献与毕业设计内容紧密相关，毕业设计正文中引用（或脚注、尾注）的文献数量不少于5项
- [x] 有专门的文献综述章（节）部分
- [x] 文档中所有的表要有表头，且表头在表的正上方
- [x] 文档中所有的图，要有图题，图题在图的正下方
- [x] 论文目录中，只包含到二级标题如（2.1），不应有三级标题（2.1.2）。
- [x] 论文章节应不少于4个章节，如果小于等于4章，则提醒章节设置太少，论文结构需调整。

## 前端效果

![preview](/doc/preview.png)

## 安装

### 平台要求

由于依赖 `pywin32`（Word COM），本项目仅支持 Windows（x64）。Linux 上可尝试 Wine/Windows 容器，但不保证稳定。
首先安装 Python 项目依赖（以 `uv` 为例） ：

```shell
uv sync
uv pip install -e .
```

接着安装前端依赖：

```shell
cd ./frontend
npm install
```

## 开发模式

1. 启动后端服务（仅本机） ：

```shell
npm run api:dev
```

默认服务会运行在 `http://localhost:8000`

2. 测试后端
访问以下URL测试后端是否正常运行:

- 根路径: `http://localhost:8000`
- 上传接口: `http://localhost:8000/upload/`

3. 启动前端
运行以下命令进入前端代码目录并启动开发服务器

```shell
npm run web:dev
```

- 前端默认监听 `127.0.0.1:5174`，可通过环境变量覆盖：
  - PowerShell：`$env:VITE_HOST='0.0.0.0'; $env:VITE_PORT=8080; npm run web:dev`
  - 或透传参数：`npm run web:dev -- --host 0.0.0.0 --port 8080`
- Vite 代理已将 `/upload` 转发到 `http://localhost:8000`，开发期前端可直接请求相对路径 `/upload/` 以减少跨域问题。

## 生产模式

1. 启动后端服务

```shell
npm run api:serve
```

监听 `0.0.0.0:8000`，启用 `--proxy-headers` 与多 workers。

2. 构建前端静态文件

```shell
npm run web:build
```

产物位于 `frontend/dist/`。

3. 预览静态产物（临时验证） ：

```shell
npm run web:preview
```

默认 `0.0.0.0:8080`.正式部署推荐使用 Nginx/任意静态服务器来托管 `frontend/dist/` 并启用缓存/HTTPS。

4. 启动网站

```shell
npm run web:start
```

默认 `0.0.0.0:80`
