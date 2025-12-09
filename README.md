# My Scoop Bucket

这是我的个人 Scoop 软件仓库，支持全自动更新。

## 软件列表

| 软件 | 仓库 | 说明 |
|------|------|------|
| ccNexus | [lich0821/ccNexus](https://github.com/lich0821/ccNexus) | Intelligent API gateway for Claude Code - rotat... |
| code-switch-R | [Rogers-F/code-switch-R](https://github.com/Rogers-F/code-switch-R) | Claude Code & Codex 多供应商代理与管理工具 |
| cc-switch | [farion1231/CC-Switch](https://github.com/farion1231/CC-Switch) | A cross-platform desktop All-in-One assistant t... |
| directory-migration-tool | [zhao-wuyan/directory-migration-tool](https://github.com/zhao-wuyan/directory-migration-tool) | 一个使用符号链接迁移大型目录的 Windows 工具，快速将文件夹迁移到其他磁盘，且保留原路径... |

## 如何使用

1. 添加仓库：
   ```powershell
   scoop bucket add my-tools https://github.com/你的用户名/softs
   ```

2. 安装软件：
   ```powershell
   scoop install my-tools/ccNexus
   ```

3. 更新软件：
   ```powershell
   scoop update ccNexus
   ```

## 自动更新

本仓库通过 GitHub Actions 每天自动检查上游仓库的新版本，并更新 manifest 文件。