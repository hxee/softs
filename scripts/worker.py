import json
import requests
import hashlib
import os
import re

# === 配置区域 ===
CONFIG_FILE = 'soft.json'
BUCKET_DIR = 'bucket'

def get_latest_release(repo):
    """获取 GitHub 最新 Release"""
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    print(f"Checking {repo}...")
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  [Error] API Request failed: {e}")
        return None

def find_asset(assets):
    """智能寻找 Windows 压缩包"""
    # 优先级：zip > 7z > exe (优先选绿色版)
    for ext in ['.zip', '.7z', '.exe']:
        for asset in assets:
            name = asset['name'].lower()
            # 必须包含 windows 关键字，且符合后缀，排除 sig 签名文件
            if 'windows' in name and name.endswith(ext) and '.sig' not in name:
                return asset
    return None

def calc_hash(url):
    """下载并计算 SHA256 (机器人干这事很快)"""
    print(f"  Downloading for hash: {url} ...")
    try:
        resp = requests.get(url, stream=True)
        sha256 = hashlib.sha256()
        for chunk in resp.iter_content(8192):
            sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        print(f"  [Error] Hash calculation failed: {e}")
        return None

def save_manifest(app_name, version, description, homepage, url, file_hash):
    """生成并保存 JSON 文件"""
    manifest = {
        "version": version,
        "description": description,
        "homepage": homepage,
        "license": "MIT",
        "url": url,
        "hash": file_hash,
        "bin": f"{app_name}.exe", # 默认假设 exe 名字和软件名一致
        "checkver": "github",
    }
    
    os.makedirs(BUCKET_DIR, exist_ok=True)
    file_path = os.path.join(BUCKET_DIR, f"{app_name}.json")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=4)
    print(f"  [Success] Saved {file_path}")

def main():
    if not os.path.exists(CONFIG_FILE):
        print(f"Config file {CONFIG_FILE} not found.")
        return

    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        apps = json.load(f)

    for app_name, repo in apps.items():
        # 1. 获取信息
        data = get_latest_release(repo)
        if not data: continue
        
        # 2. 找文件
        asset = find_asset(data['assets'])
        if not asset:
            print(f"  [Skip] No suitable Windows asset found for {app_name}")
            continue
            
        # 3. 算 Hash
        file_hash = calc_hash(asset['browser_download_url'])
        if not file_hash: continue
        
        # 4. 生成文件
        version = data['tag_name'].lstrip('v') # 去掉 v 前缀
        description = f"{app_name} auto-generated from {repo}"
        save_manifest(app_name, version, description, data['html_url'], asset['browser_download_url'], file_hash)

if __name__ == "__main__":
    main()