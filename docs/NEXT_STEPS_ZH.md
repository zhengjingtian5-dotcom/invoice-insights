# 下一步

本次未修改 Python 脚本。把新 README.md、.gitignore、requirements.txt 和 docs
文件夹复制回原项目即可。保留原来的 data、outputs 和 .venv 文件夹。

## 固定依赖版本

在已经成功运行页面的原项目终端中执行：

```powershell
.\.venv\Scripts\python.exe -m pip show streamlit
```

找到 Version，把 requirements.txt 中的 streamlit 改为 streamlit==实际版本号。
不要把“实际版本号”几个字写进去。

## 准备展示

只截应用内容，避免包含浏览器标签、书签和账号头像。可保存到
docs/screenshots/，然后在 README 添加相应图片链接。

上传 GitHub 时上传解压后的源文件和 docs 文件夹，不是只上传 ZIP。
不上传 .venv、data、outputs 或密码文件。新 .gitignore 已包含这些常见排除规则。
如果这些文件之前已经被 Git 跟踪，新增 .gitignore 不会自动取消跟踪。

本包不含数据和数据库。新电脑运行时按照 README 下载数据并重建。
现有 README 的金额与规则针对 UCI 原始数据集，不适用于任意其他 Excel。
