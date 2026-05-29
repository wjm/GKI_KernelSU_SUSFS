#!/usr/bin/env python3
import os
import sys
import json
import tarfile
import urllib.request
import ssl
from pathlib import Path
from typing import Optional


class CacheManager:
    def __init__(self, repo: str):
        self.repo = repo
        self.ccache_dir = Path.home() / ".ccache"
        self.cache_dir = Path.home() / ".cache"

    def get_latest_release(self) -> Optional[dict]:
        """获取最新的 Release"""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        try:
            url = f"https://api.github.com/repos/{self.repo}/releases/latest"
            req = urllib.request.Request(url, headers={'User-Agent': 'Python'})
            with urllib.request.urlopen(req, context=ssl_context) as response:
                return json.loads(response.read())
        except Exception as e:
            print(f"获取最新 Release 失败: {e}")
            return None

    def get_cache_url(self) -> Optional[str]:
        """获取缓存文件的下载 URL"""
        release = self.get_latest_release()
        if not release:
            return None

        for asset in release.get('assets', []):
            if asset['name'] == 'build-cache.tar.xz':
                return asset['browser_download_url']

        return None

    def download_cache(self) -> bool:
        """下载并解压缓存"""
        cache_url = self.get_cache_url()
        if not cache_url:
            print("未找到缓存文件，跳过")
            return False

        print(f"下载缓存: {cache_url}")

        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            req = urllib.request.Request(cache_url, headers={'User-Agent': 'Python'})
            with urllib.request.urlopen(req, context=ssl_context) as response:
                data = response.read()
                cache_file = Path.home() / "build-cache.tar.xz"
                with open(cache_file, 'wb') as f:
                    f.write(data)

            print("解压缓存...")
            with tarfile.open(cache_file, 'r:xz') as tar:
                tar.extractall(str(Path.home()))
            cache_file.unlink()
            print("缓存恢复完成")
            return True

        except Exception as e:
            print(f"下载缓存失败: {e}")
            return False

    def save_cache(self) -> bool:
        """打包并保存缓存"""
        if not self.ccache_dir.exists() and not self.cache_dir.exists():
            print("没有找到缓存目录，跳过保存")
            return False

        print("打包缓存...")

        try:
            self.ccache_dir.mkdir(parents=True, exist_ok=True)
            self.cache_dir.mkdir(parents=True, exist_ok=True)

            cache_file = Path.cwd() / "build-cache.tar.xz"

            with tarfile.open(cache_file, 'w:xz') as tar:
                if self.ccache_dir.exists():
                    tar.add(self.ccache_dir, arcname='.ccache')
                if self.cache_dir.exists():
                    tar.add(self.cache_dir, arcname='.cache')

            print(f"缓存已打包: {cache_file}")
            return True

        except Exception as e:
            print(f"保存缓存失败: {e}")
            return False

    def get_cache_version(self) -> Optional[str]:
        """获取最新缓存版本"""
        release = self.get_latest_release()
        if not release:
            return None

        for asset in release.get('assets', []):
            if asset['name'] == 'build-cache.tar.xz':
                return str(release['tag_name'])

        return None


def main():
    if len(sys.argv) < 2:
        print("用法: python cache_manager.py <download|save|get-version> [repo]")
        sys.exit(1)

    action = sys.argv[1]
    repo = os.environ.get('GITHUB_REPOSITORY', '')
    if not repo and len(sys.argv) > 2:
        repo = sys.argv[2]

    if action != 'save' and not repo:
        print("错误: 未指定仓库")
        sys.exit(1)

    cache_manager = CacheManager(repo)

    if action == 'download':
        success = cache_manager.download_cache()
        sys.exit(0 if success else 1)

    elif action == 'save':
        success = cache_manager.save_cache()
        sys.exit(0 if success else 1)

    elif action == 'get-version':
        version = cache_manager.get_cache_version()
        if version:
            print("version=" + version)
            with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
                f.write('version=' + version + '\n')
        else:
            print("未找到缓存版本")
        sys.exit(0)

    else:
        print(f"未知操作: {action}")
        print("可用操作: download, save, get-version")
        sys.exit(1)


if __name__ == '__main__':
    main()
