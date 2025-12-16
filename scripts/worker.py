import json
import requests
import hashlib
import os
import re

CONFIG_FILE = 'soft.json'
BUCKET_DIR = 'bucket'
README_FILE = 'README.md'

# 架构关键词映射
ARCH_PATTERNS = {
    '64bit': ['amd64', 'x86_64', 'x64', 'win64'],
    'arm64': ['arm64', 'aarch64'],
    '32bit': ['386', 'i386', 'x86', 'win32']
}

def get_github_headers():
    """获取 GitHub API 请求头，支持 Token 认证"""
    headers = {'Accept': 'application/vnd.github.v3+json'}
    token = os.environ.get('GITHUB_TOKEN')
    if token:
        headers['Authorization'] = f'token {token}'
    return headers

def get_repo_info(repo):
    """获取仓库基本信息（description, license 等）"""
    url = f"https://api.github.com/repos/{repo}"
    try:
        resp = requests.get(url, headers=get_github_headers())
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  [Warn] Failed to get repo info: {e}")
        return None

def get_latest_release(repo):
    """获取最新 Release 信息"""
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    print(f"Checking {repo}...")
    try:
        resp = requests.get(url, headers=get_github_headers())
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  [Error] API Request failed: {e}")
        return None

def detect_arch(filename):
    """检测文件对应的架构"""
    name = filename.lower()
    for arch, patterns in ARCH_PATTERNS.items():
        for pattern in patterns:
            if pattern in name:
                return arch
    return None

def is_valid_asset(asset):
    """检查是否为有效的 Windows 安装包"""
    name = asset['name'].lower()
    excluded = ['.sig', '.asc', '.sha256', '.md5', 'source', 'src', 'linux', 'darwin', 'macos']
    if any(ex in name for ex in excluded):
        return False
    valid_ext = ['.zip', '.7z', '.exe', '.msi']
    if not any(name.endswith(ext) for ext in valid_ext):
        return False
    if 'windows' in name or 'win' in name:
        return True
    return True

def find_assets_by_arch(assets):
    """按架构分类查找资产，返回 {arch: asset} 字典"""
    result = {}
    ext_priority = ['.zip', '.7z', '.exe', '.msi']
    valid_assets = [a for a in assets if is_valid_asset(a)]
    
    for asset in valid_assets:
        arch = detect_arch(asset['name'])
        if not arch:
            arch = '64bit'
        
        if arch in result:
            current_ext = next((e for e in ext_priority if result[arch]['name'].lower().endswith(e)), None)
            new_ext = next((e for e in ext_priority if asset['name'].lower().endswith(e)), None)
            if new_ext and current_ext and ext_priority.index(new_ext) < ext_priority.index(current_ext):
                result[arch] = asset
        else:
            result[arch] = asset
    return result

def calc_hash(url):
    """下载文件并计算 SHA256"""
    print(f"  Downloading for hash: {url} ...")
    try:
        resp = requests.get(url, stream=True, headers=get_github_headers())
        resp.raise_for_status()
        sha256 = hashlib.sha256()
        for chunk in resp.iter_content(8192):
            sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        print(f"  [Error] Hash calculation failed: {e}")
        return None

def build_autoupdate(repo, arch_assets):
    """构建 autoupdate 配置"""
    autoupdate = {"architecture": {}}
    for arch, asset in arch_assets.items():
        url_template = re.sub(r'v?\d+\.\d+\.\d+', '$version', asset['browser_download_url'])
        autoupdate["architecture"][arch] = {"url": url_template}
    return autoupdate

def save_manifest(app_name, version, description, homepage, license_name, arch_assets, repo, bin_override=None):
    """保存 Scoop manifest 文件"""
    # 【修改点 1】优先使用 bin_override
    final_bin = bin_override if bin_override else f"{app_name}.exe"

    manifest = {
        "version": version,
        "description": description,
        "homepage": homepage,
        "license": license_name,
        "architecture": {},
        "bin": final_bin, # 【修改点 1】应用变量
        "checkver": "github",
        "autoupdate": build_autoupdate(repo, arch_assets)
    }
    
    for arch, asset in arch_assets.items():
        file_hash = calc_hash(asset['browser_download_url'])
        if not file_hash:
            print(f"  [Error] Failed to calculate hash for {arch}")
            continue
        manifest["architecture"][arch] = {
            "url": asset['browser_download_url'],
            "hash": file_hash
        }
    
    if not manifest["architecture"]:
        print(f"  [Error] No valid assets found for {app_name}")
        return False
    
    os.makedirs(BUCKET_DIR, exist_ok=True)
    file_path = os.path.join(BUCKET_DIR, f"{app_name}.json")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=4, ensure_ascii=False)
    print(f"  [Success] Saved {file_path}")
    return True

def update_readme(app_info_list):
    """更新 README.md"""
    if not os.path.exists(README_FILE):
        print(f"  [Warn] {README_FILE} not found, skipping README update")
        return
    
    with open(README_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    table_header = "| 软件 | 仓库 | 说明 |\n|------|------|------|\n"
    table_rows = []
    for app_name, repo, description in app_info_list:
        if description and len(description) > 50:
            description = description[:47] + "..."
        desc = description or f"{app_name} 工具"
        table_rows.append(f"| {app_name} | [{repo}](https://github.com/{repo}) | {desc} |")
    
    new_table = table_header + "\n".join(table_rows)
    pattern = r'(## 软件列表\s*\n+)(\|[^\n]+\|\s*\n)+(\s*)'
    replacement = r'\g<1>' + new_table + '\n\n'
    
    new_content = re.sub(pattern, replacement, content)
    
    if new_content != content:
        with open(README_FILE, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"  [Success] Updated {README_FILE}")
    else:
        print(f"  [Skip] {README_FILE} is already up to date")

def main():
    if not os.path.exists(CONFIG_FILE):
        print(f"Config file {CONFIG_FILE} not found.")
        return

    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        apps = json.load(f)

    app_info_list = []

    # 【修改点 2】解析配置：支持字符串或字典
    for app_name, config in apps.items():
        if isinstance(config, dict):
            repo = config.get('repo')
            custom_bin = config.get('bin')
        else:
            repo = config
            custom_bin = None
        
        if not repo: continue
        
        # 1. 获取仓库信息
        repo_info = get_repo_info(repo)
        description = repo_info.get('description', f'{app_name} - auto-generated') if repo_info else f'{app_name} - auto-generated'
        app_info_list.append((app_name, repo, description))
        
        # 2. 获取最新 Release
        release_data = get_latest_release(repo)
        if not release_data: continue
        latest_version = release_data['tag_name'].lstrip('v')
        
        # 3. 检查本地版本
        local_file = os.path.join(BUCKET_DIR, f"{app_name}.json")
        if os.path.exists(local_file):
            try:
                with open(local_file, 'r', encoding='utf-8') as f:
                    local_manifest = json.load(f)
                if local_manifest.get('version') == latest_version:
                    print(f"  [Skip] {app_name} is already up to date ({latest_version})")
                    continue
            except: pass
        
        print(f"  [Update] Found new version: {latest_version}")
        
        # 4. 获取其他信息
        homepage = f"https://github.com/{repo}"
        license_name = 'Unknown'
        if repo_info and repo_info.get('license'):
            license_name = repo_info['license'].get('spdx_id', 'Unknown')
        
        # 5. 查找资产
        arch_assets = find_assets_by_arch(release_data['assets'])
        if not arch_assets:
            print(f"  [Skip] No suitable Windows asset found for {app_name}")
            continue
        print(f"  [Info] Found architectures: {list(arch_assets.keys())}")
        
        # 6. 保存 manifest
        # 【修改点 3】传入 custom_bin
        save_manifest(app_name, latest_version, description, homepage, license_name, arch_assets, repo, custom_bin)
    
    if app_info_list:
        print("\nUpdating README.md...")
        update_readme(app_info_list)

if __name__ == "__main__":
    main()