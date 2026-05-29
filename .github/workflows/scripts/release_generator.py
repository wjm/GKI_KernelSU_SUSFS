#!/usr/bin/env python3
import json
import urllib.request
import ssl
import sys
from pathlib import Path


class ReleaseGenerator:
    def __init__(self):
        self.matrix_path = Path(__file__).parent.parent / "config" / "matrix.json"
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    def load_matrix(self) -> dict:
        """加载构建矩阵"""
        with open(self.matrix_path, 'r') as f:
            return json.load(f)

    def get_ksu_info(self) -> tuple:
        """获取 SukiSU 的 tag 和 commit"""
        ksu_tag = "latest"
        ksu_commit = "unknown"

        try:
            tags_url = "https://api.github.com/repos/SukiSU-Ultra/SukiSU-Ultra/git/refs/tags"
            req = urllib.request.Request(tags_url, headers={'User-Agent': 'Python'})
            with urllib.request.urlopen(req, context=self.ssl_context) as response:
                tags = json.loads(response.read())
                if tags:
                    ksu_tag = tags[-1]['ref'].split('/')[-1]
        except Exception as e:
            print(f"获取 KSU tag 失败: {e}")

        try:
            commits_url = "https://api.github.com/repos/SukiSU-Ultra/SukiSU-Ultra/git/ref/heads/main"
            req = urllib.request.Request(commits_url, headers={'User-Agent': 'Python'})
            with urllib.request.urlopen(req, context=self.ssl_context) as response:
                ref = json.loads(response.read())
                ksu_commit = ref['object']['sha'][:7]
        except Exception as e:
            print(f"获取 KSU commit 失败: {e}")

        return ksu_tag, ksu_commit

    def generate_body(self) -> str:
        """生成 release body"""
        matrix = self.load_matrix()
        ksu_tag, ksu_commit = self.get_ksu_info()

        configs = []
        for key in sorted(matrix.keys()):
            android, kernel = key.split('-')
            version = android.replace('android', '')
            configs.append("- Android " + version + " (Kernel " + kernel + ")")

        lines = [
            "## GKI Kernel with SukiSU & SUSFS v2.1.0",
            "",
            "### SukiSU Info",
            "- Tag: `" + ksu_tag + "`",
            "- Commit: `" + ksu_commit + "`",
            "",
            "### Supported Configurations",
        ]
        lines.extend(configs)
        lines.extend([
            "",
            "### Features",
            "- SUSFS v2.1.0",
            "- Manual Syscall Hooks",
            "- Magic Mount Support",
            "- BBR Support",
            "- LZ4KD Support",
        ])

        return '\n'.join(lines)

    def save_body(self, output_path: str = "RELEASE_BODY.md"):
        """保存 release body 到文件"""
        body = self.generate_body()
        with open(output_path, 'w') as f:
            f.write(body)
        print(body)
        return body


def main():
    output_path = sys.argv[1] if len(sys.argv) > 1 else "RELEASE_BODY.md"
    generator = ReleaseGenerator()
    generator.save_body(output_path)


if __name__ == '__main__':
    main()
