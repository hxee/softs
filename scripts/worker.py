import json
import requests
import hashlib
import os
import re

CONFIG_FILE = 'soft.json'
BUCKET_DIR = 'bucket'

def get_latest_release(repo):
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
    # 优先级：zip > 7z > exe (优先选绿色版)
    for ext in ['.zip', '.7z', '.exe']:
        for asset in assets:
            name = asset['name'].lower()
            if 'windows' in name and name.endswith(ext) and '.sig' not in name:
                return asset
    return None

def calc_hash(url):
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
    manifest = {
        "version": version,
        "description": description,
        "homepage": homepage,
        "license": "MIT",
        "url": url,
        "hash": file_hash,
        "bin": f"{app_name}.exe",
        "checkver": "github",
    }
    
    os.makedirs(BUCKET_DIR, exist_ok=True)
    file_path = os.path.join(BUCKET_DIR, f"{app_name}.json")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=4)
    print(f"  [Success] Saved {file_path}")

# === 核心修改在这里 ===
def main():
    if not os.path.exists(CONFIG_FILE):
        print(f"Config file {CONFIG_FILE} not found.")
        return

    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        apps = json.load(f)

    for app_name, repo in apps.items():
        # 1. 获取最新 Release 信息
        data = get_latest_release(repo)
        if not data: continue
        
        latest_version = data['tag_name'].lstrip('v') # 去掉 v
        
        # 2. 【新增】检查本地是否有旧版本
        local_file = os.path.join(BUCKET_DIR, f"{app_name}.json")
        if os.path.exists(local_file):
            try:
                with open(local_file, 'r', encoding='utf-8') as f:
                    local_manifest = json.load(f)
                # 如果版本一样，直接跳过！
                if local_manifest.get('version') == latest_version:
                    print(f"  [Skip] {app_name} is already up to date ({latest_version})")
                    continue
            except:
                pass # 如果读取本地文件出错，就当它不存在，继续更新

        # 3. 如果版本不一样，或者本地没文件，才开始干重活（下载）
        print(f"  [Update] Found new version: {latest_version}")
        
        asset = find_asset(data['assets'])
        if not asset:
            print(f"  [Skip] No suitable Windows asset found for {app_name}")
            continue
            
        file_hash = calc_hash(asset['browser_download_url'])
        if not file_hash: continue
        
        description = f"{app_name} auto-generated from {repo}"
        save_manifest(app_name, latest_version, description, data['html_url'], asset['browser_download_url'], file_hash)

if __name__ == "__main__":
    main()