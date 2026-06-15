# file-lister

一个简洁高效的文件清单生成工具，支持本地和网络路径扫描，可按文件类型筛选并生成 HTML 和 CSV 格式的报告。

## 功能特性

- **文件夹扫描**：扫描指定文件夹，支持本地路径和网络路径
- **子文件夹控制**：可选择是否递归扫描子文件夹
- **文件类型筛选**：自动识别文件夹内的所有文件类型，支持按扩展名筛选
- **报告生成**：生成 HTML 和 CSV 两种格式的文件清单报告
- **实时预览**：在界面中直接预览文件列表，支持关键字搜索和类型筛选
- **主题切换**：内置多种界面主题，可自由切换
- **独立运行**：支持打包为独立的 exe 可执行文件

## 安装

### 方式一：直接运行（需要 Python 环境）

```bash
# 克隆仓库
git clone https://github.com/caifugao110/file-lister.git
cd file-lister

# 安装依赖
pip install -r requirements.txt

# 运行程序
python app.py
```

### 方式二：打包为 exe 文件

```powershell
# 在项目根目录执行构建脚本
.\scripts\build_exe.ps1
```

构建完成后，可执行文件位于 `dist\file-lister.exe`。

## 使用方法

1. **选择文件夹**：点击"选择"按钮，选择要扫描的文件夹
2. **配置选项**：
   - 勾选"包含子文件夹"可递归扫描所有子目录
   - 在"动态文件格式"区域选择需要包含的文件类型
3. **开始扫描**：点击"获取文件清单"按钮
4. **查看结果**：
   - 在右侧表格中查看扫描结果
   - 使用筛选功能过滤文件
   - 点击"打开生成报告"查看 HTML 报告
   - 点击"打开文件清单"查看 CSV 文件

## 报告说明

扫描完成后，会在程序目录下的 `reports` 文件夹中生成两个文件：

- `filelist_YYYYMMDD_HHMMSS.csv` - CSV 格式文件清单
- `filelist_YYYYMMDD_HHMMSS.html` - HTML 格式报告（支持筛选和搜索）

## 技术栈

- **GUI 框架**：ttkbootstrap（基于 tkinter）
- **打包工具**：PyInstaller
- **Python 版本**：>= 3.9

## 项目结构

```
file-lister/
├── app.py              # 主程序入口
├── assets/
│   └── app.ico         # 应用图标
├── scripts/
│   └── build_exe.ps1   # Windows 打包脚本
├── pyproject.toml      # 项目配置
├── requirements.txt    # 依赖列表
└── LICENSE             # MIT 许可证
```

## 许可证

本项目采用 [MIT](LICENSE) 许可证。