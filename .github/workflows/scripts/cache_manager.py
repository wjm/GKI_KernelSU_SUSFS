#!/usr/bin/env python3
import os
import sys
import json
import tarfile
import urllib.request
import ssl
import subprocess
from pathlib import Path
from typing import Optional


class CacheManager:
    def __init__(self, repo: str, branch: str = None):
        self.repo = repo
        self.branch = branch or self._get_current_branch()
        self.ccache_dir = Path.home() / ".ccache"
        self.cache_dir = Path.home() / ".cache"

    def _get_current_branch(self) -> str:
        try:
            branch = os.environ.get('GITHUB_REF_NAME', '')
            if branch:
                return branch.replace('/', '-').replace(' ', '-')

            result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                                   capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip().replace('/', '-').replace(' ', '-')
        except Exception:
            pass
        return 'unknown'

    def _get_ssl_context(self) -> ssl.SSLContext:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def _make_request(self, url: str) -> Optional[dict]:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Python'})
            with urllib.request.urlopen(req, context=self._get_ssl_context()) as response:
                return json.loads(response.read())
        except Exception as e:
            print(f"请求失败: {e}")
            return None

    def get_latest_release(self) -> Optional[dict]:
        return self._make_request(f"https://api.github.com/repos/{self.repo}/releases/latest")

    def get_cache_url(self, cache_filename: str) -> Optional[str]:
        release = self.get_latest_release()
        if not release:
            return None
        for asset in release.get('assets', []):
            if asset['name'] == cache_filename:
                return asset['browser_download_url']
        return None

    def download_cache(self, android: str, kernel: str, sub_level: str) -> bool:
        cache_filename = f"build-cache-{self.branch}-{android}-{kernel}-{sub_level}.tar.xz"
        cache_url = self.get_cache_url(cache_filename)

        if not cache_url:
            print(f"未找到缓存: {cache_filename}，跳过下载")
            return False

        try:
            req = urllib.request.Request(cache_url, headers={'User-Agent': 'Python'})
            with urllib.request.urlopen(req, context=self._get_ssl_context()) as response:
                cache_file = Path.home() / cache_filename
                with open(cache_file, 'wb') as f:
                    f.write(response.read())

            with tarfile.open(cache_file, 'r:xz') as tar:
                tar.extractall(str(Path.home()))
            cache_file.unlink()
            print("缓存恢复完成")
            return True
        except Exception as e:
            print(f"下载缓存失败: {e}")
            return False

    def save_cache(self, android: str, kernel: str, sub_level: str) -> bool:
        if not self.ccache_dir.exists() and not self.cache_dir.exists():
            print("没有找到缓存目录，跳过保存")
            return False

        cache_filename = f"build-cache-{self.branch}-{android}-{kernel}-{sub_level}.tar.xz"
        try:
            self.ccache_dir.mkdir(parents=True, exist_ok=True)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = Path.home() / cache_filename

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
        release = self.get_latest_release()
        return str(release['tag_name']) if release else None


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python cache_manager.py download <repo> <branch> <android> <kernel> <sub_level>")
        print("  python cache_manager.py save <repo> <branch> <android> <kernel> <sub_level>")
        print("  python cache_manager.py get-version <repo>")
        sys.exit(1)

    action = sys.argv[1]

    if action == 'download':
        if len(sys.argv) < 7:
            print("错误: download 需要 <repo> <branch> <android> <kernel> <sub_level>")
            sys.exit(1)
        cache_manager = CacheManager(sys.argv[2], sys.argv[3])
        success = cache_manager.download_cache(sys.argv[4], sys.argv[5], sys.argv[6])
        sys.exit(0 if success else 1)

    elif action == 'save':
        if len(sys.argv) < 7:
            print("错误: save 需要 <repo> <branch> <android> <kernel> <sub_level>")
            sys.exit(1)
        cache_manager = CacheManager(sys.argv[2], sys.argv[3])
        success = cache_manager.save_cache(sys.argv[4], sys.argv[5], sys.argv[6])
        sys.exit(0 if success else 1)

    elif action == 'get-version':
        if len(sys.argv) < 3:
            print("错误: get-version 需要 <repo>")
            sys.exit(1)
        cache_manager = CacheManager(sys.argv[2])
        version = cache_manager.get_cache_version()
        if version:
            print("version=" + version)
            with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
                f.write('version=' + version + '\n')
        sys.exit(0)

    else:
        print(f"未知操作: {action}")
        sys.exit(1)


if __name__ == '__main__':
    main()
