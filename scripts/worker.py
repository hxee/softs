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

def calc_hash(url):
    print(f"  Downloading hash: {url} ...")
    try:
        resp = requests.get(url, stream=True)
        sha256 = hashlib.sha256()
        for chunk in resp.iter_content(8192):
            sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        print(f"  [Error] Hash calc failed: {e}")
        return None

def analyze_architecture(assets):
    """
    智能分析所有 Asset，按架构分类
    返回结构: { '64bit': {'url':..., 'hash':...}, '32bit': ... }
    """
    arch_map = {}
    
    # 定义架构关键词匹配规则 (正则)
    rules = [
        ('64bit', r'(x64|amd64|win64)'),
        ('32bit', r'(x86|win32)'),
        ('arm64', r'(arm64)'),
    ]

    for asset in assets:
        name = asset['name'].lower()
        if not name.endswith('.zip') or 'windows' not in name or '.sig' in name:
            continue
            
        url = asset['browser_download_url']
        
        # 匹配架构
        for arch_name, pattern in rules:
            if re.search(pattern, name):
                print(f"  Found {arch_name} asset: {name}")
                file_hash = calc_hash(url)
                if file_hash:
                    arch_map[arch_name] = {
                        "url": url,
                        "hash": file_hash
                    }
                break # 找到一种架构后就跳过后续匹配
    
    # 如果没匹配到任何具体架构，但有 zip，默认算作 64bit (兜底策略)
    if not arch_map:
        for asset in assets:
            name = asset['name'].lower()
            if name.endswith('.zip') and 'windows' in name and '.sig' not in name:
                print(f"  Fallback to 64bit for: {name}")
                file_hash = calc_hash(asset['browser_download_url'])
                if file_hash:
                    arch_map['64bit'] = {
                        "url": asset['browser_download_url'],
                        "hash": file_hash
                    }
                break

    return arch_map

def save_manifest(app_name, repo_data, arch_data):
    version = repo_data['tag_name'].lstrip('v')
    
    manifest = {
        "version": version,
        "description": f"{app_name} from {repo_data['html_url']}",
        "homepage": repo_data['html_url'],
        "license": "MIT",
        "bin": f"{app_name}.exe",
        "checkver": "github",
        "architecture": arch_data  # 这里变成了结构化的数据
    }
    
    os.makedirs(BUCKET_DIR, exist_ok=True)
    file_path = os.path.join(BUCKET_DIR, f"{app_name}.json")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=4)
    print(f"  [Success] Saved {file_path}")

def main():
    if not os.path.exists(CONFIG_FILE): return
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        apps = json.load(f)

    for app_name, repo in apps.items():
        data = get_latest_release(repo)
        if not data: continue
        
        # 这一步变成了智能分析
        arch_data = analyze_architecture(data['assets'])
        
        if not arch_data:
            print(f"  [Skip] No suitable assets found for {app_name}")
            continue
            
        save_manifest(app_name, data, arch_data)

if __name__ == "__main__":
    main()