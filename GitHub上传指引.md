# GitHub 上传指引 — AI Assignment #3

复用账号 Tramsehoi，两分钟搞定。报告第 6 节已写了这个地址，仓库名请保持一致。

## 1. 建仓库

1. 打开 https://github.com/new
2. Repository name 填：`cisc3024-ai-assignment3-rpca`（与报告第 6 节链接一致；如改名，告诉我，我更新报告）
3. 选 **Public**（报告里写了 public repository，老师要能打开）
4. 不要勾选任何初始化文件（README 等），直接 Create repository

## 2. 上传代码（网页上传，最简单）

在新建仓库页面点 **"uploading an existing file"**，把下面这些文件拖进去：

```
C:\Users\asus\WorkBuddy\2026-09-14-14-57-43\ai_assignment3\README.md
C:\Users\asus\WorkBuddy\2026-09-14-14-57-43\ai_assignment3\requirements.txt
C:\Users\asus\WorkBuddy\2026-09-14-14-57-43\ai_assignment3\src\rpca.py
C:\Users\asus\WorkBuddy\2026-09-14-14-57-43\ai_assignment3\results\fig_synthetic.png
C:\Users\asus\WorkBuddy\2026-09-14-14-57-43\ai_assignment3\results\fig_video.png
C:\Users\asus\WorkBuddy\2026-09-14-14-57-43\ai_assignment3\results\fig_convergence.png
C:\Users\asus\WorkBuddy\2026-09-14-14-57-43\ai_assignment3\results\stats_synthetic.json
C:\Users\asus\WorkBuddy\2026-09-14-14-57-43\ai_assignment3\results\stats_video.json
```

> `data/vtest.avi`（8 MB 视频）**不用传**，README 里写了下载命令。保持仓库干净。
> 若想保留 `src/` 和 `results/` 目录结构，网页上传时可以先建一个空文件 `src/.gitkeep`，
> 或直接在 GitHub 网页上用 "Create new file" 输入带路径的文件名。

Commit message 写 `Add AI-generated RPCA background subtraction` 即可，点 **Commit changes**。

## 3. 验证

打开 `https://github.com/Tramsehoi/cisc3024-ai-assignment3-rpca`，确认能看到 README 渲染、
`src/rpca.py` 和 3 张结果图。

## 4. 回填报告链接

建好后发我一句确认（或把实际地址发我）。如果仓库名按上面填，报告第 6 节的链接已经正确，
我会再验证一次链接可达，然后定稿 docx。
