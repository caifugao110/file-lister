<p align="center">
  <h1 align="center">file-lister</h1>
  <p align="center">
    <img src="https://img.shields.io/github/v/release/caifugao110/file-lister?color=blue" alt="version">
    <img src="https://img.shields.io/badge/python-%3E%3D3.9-green" alt="python">
    <img src="https://img.shields.io/badge/license-MIT-yellow" alt="license">
    <img src="https://img.shields.io/badge/platform-Windows-lightgrey" alt="platform">
  </p>
  <p align="center">
    <i>A polished Python desktop GUI tool for generating file listings with HTML and CSV reports.</i>
  </p>
</p>

---

## 简介

**file-lister** 是一款基于 Python 的桌面 GUI 文件清单生成工具，用于扫描指定文件夹，支持按文件类型筛选，并生成 HTML 和 CSV 格式的文件清单报告。

| 项目信息 |  |
| --- | --- |
| 作者 | **caifugao110** |
| 项目地址 | [github.com/caifugao110/file-lister](https://github.com/caifugao110/file-lister) |
| 开源协议 | MIT |

---

## 功能特性

### 路径支持
- 支持 **本地路径** 和 **局域网 UNC 路径**（如 `\\192.168.1.100\SharedFolder`）

### 扫描模式
- 包含子文件夹的 **递归扫描**（可选）
- 自动识别文件夹内的所有文件类型
- 支持 **按扩展名筛选**，仅扫描指定格式

### 结果与操作
- 生成 **CSV** 和 **可筛选的 HTML** 文件清单报告
- GUI 实时预览文件列表，支持关键字搜索和类型筛选
- 一键打开生成的 HTML 报告或 CSV 文件
- GUI 支持 **多主题切换**（默认主题：yeti）

---

## 快速开始

### 环境要求

- Python >= 3.9
- Windows 操作系统

### 直接运行源码

```powershell
pip install -r requirements.txt
python .\app.py
```

---

## 构建

### 打包为单文件 exe

```powershell
.\scripts\build_exe.ps1
```

构建完成后保留产物：

```
dist\file-lister.exe
```

> 构建脚本会自动创建临时虚拟环境、安装依赖、生成图标、调用 PyInstaller，并在结束后清理 `.venv`、`build`、spec 文件、缓存和临时报告等过程文件。

---

## 项目结构

```
file-lister/
├── app.py                  # GUI 主程序，包含全部核心逻辑
├── assets/
│   └── app.ico             # 应用图标
├── scripts/
│   └── build_exe.ps1       # Windows 构建脚本
├── .github/
│   └── workflows/
│       └── release.yml     # GitHub Actions 自动发布工作流
├── .gitignore
├── LICENSE
├── pyproject.toml
├── README.md
└── requirements.txt
```

| 条目 | 说明 |
| --- | --- |
| `app.py` | GUI 主程序，包含全部核心逻辑 |
| `assets/` | 图标资源 |
| `scripts/` | 构建脚本 |
| `.github/workflows/` | GitHub Actions 工作流配置 |
| `pyproject.toml` | 项目元数据与依赖配置 |
| `requirements.txt` | pip 依赖清单 |

---

## License

MIT © caifugao110