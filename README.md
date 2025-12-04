# My Scoop Bucket

这是我的个人 Scoop 软件仓库，支持全自动更新。

## 软件列表

| 软件 | 仓库 | 说明 |
|------|------|------|
| ccNexus | [lich0821/ccNexus](https://github.com/lich0821/ccNexus) | ccNexus 工具 |
| cc-switch | [farion1231/CC-Switch](https://github.com/farion1231/CC-Switch) | CC-Switch 切换工具 |

## 如何使用

1. 添加仓库：
   ```powershell
   scoop bucket add my-tools https://github.com/你的用户名/softs
   ```

2. 安装软件：
   ```powershell
   scoop install my-tools/ccNexus
   scoop install my-tools/cc-switch
   ```

3. 更新软件：
   ```powershell
   scoop update ccNexus
   scoop update cc-switch
   ```

## 自动更新

本仓库通过 GitHub Actions 每天自动检查上游仓库的新版本，并更新 manifest 文件。