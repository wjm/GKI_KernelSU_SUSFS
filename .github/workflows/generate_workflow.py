#!/usr/bin/env python3
import json
import sys
from pathlib import Path

TEMPLATE = """name: Build All Kernels

permissions:
  contents: write
  actions: write

on:
  workflow_dispatch:
    inputs:
      kernelsu_version:
        description: 'SukiSU 版本'
        required: true
        type: choice
        options:
          - Stable(标准)
          - Dev(开发)
        default: Stable(标准)
      kernelsu_commit:
        description: '指定 SukiSU commit hash (可选，留空使用最新)'
        required: false
        type: string
        default: ''
      susfs_commit:
        description: '指定 SUSFS commit hash 或相对偏移 (如 HEAD~1)'
        required: false
        type: string
        default: ''
      use_zram:
        description: '启用 ZRAM (LZ4KD)'
        required: true
        type: boolean
        default: false
      use_kpm:
        description: '启用 KPM'
        required: true
        type: boolean
        default: true
      BBG:
        description: '启用 Baseband-guard'
        required: true
        type: boolean
        default: false
      make_release:
        description: '创建 GitHub Release'
        required: true
        type: boolean
        default: true
      custom_version:
        description: '自定义版本名称 (可选)'
        required: false
        type: string
        default: ''

env:
  PYTHON_VERSION: '3.10'
  KSU_VERSION: ${{ github.event.inputs.kernelsu_version }}
  KSU_COMMIT: ${{ github.event.inputs.kernelsu_commit }}
  SUSFS_COMMIT: ${{ github.event.inputs.susfs_commit }}
  USE_ZRAM: ${{ github.event.inputs.use_zram }}
  USE_KPM: ${{ github.event.inputs.use_kpm }}
  USE_BBG: ${{ github.event.inputs.BBG }}
  MAKE_RELEASE: ${{ github.event.inputs.make_release }}
  CUSTOM_VERSION: ${{ github.event.inputs.custom_version }}

jobs:
{matrix_jobs}

  release:
    needs: [{job_names}]
    if: ${{ github.event.inputs.make_release == 'true' }}
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Download all artifacts
        uses: actions/download-artifact@v4
        with:
          path: all-artifacts
          pattern: '*_kernel-*'
          merge-multiple: true

      - name: Generate checksums
        run: |
          echo "=== Creating checksums ==="
          sha256sum * > SHA256SUMS.txt

      - name: Get SukiSU info
        run: |
          KSU_TAG=$(git ls-remote --tags https://github.com/SukiSU-Ultra/SukiSU-Ultra.git | grep -o 'refs/tags/.*' | cut -d'/' -f3 | head -n1 || echo "latest")
          KSU_COMMIT=$(git ls-remote https://github.com/SukiSU-Ultra/SukiSU-Ultra.git refs/heads/main | awk '{{ print $1 }}' | cut -c1-7)
          echo "KSU_TAG=$KSU_TAG" >> $GITHUB_ENV
          echo "KSU_COMMIT=$KSU_COMMIT" >> $GITHUB_ENV
          echo "RELEASE_NAME=GKI Kernel: SukiSU ($KSU_TAG) & SUSFS v2.1.0" >> $GITHUB_ENV

      - name: Create release
        uses: softprops/action-gh-release@v2
        with:
          tag_name: v2.1.0-${{ github.run_number }}
          name: ${{ env.RELEASE_NAME }}
          draft: true
          files: |
            *AnyKernel3*.zip
            *.img
            SHA256SUMS.txt
          body: |
            ## GKI Kernel with SukiSU & SUSFS v2.1.0

            ### SukiSU Info
            - Tag: `${{ env.KSU_TAG }}`
            - Commit: `${{ env.KSU_COMMIT }}`

            ### Supported Configurations
            - Android 12 (Kernel 5.10)
            - Android 13 (Kernel 5.10, 5.15)
            - Android 14 (Kernel 5.15, 6.1)
            - Android 15 (Kernel 6.6)

            ### Features
            - SUSFS v2.1.0
            - Manual Syscall Hooks
            - Magic Mount Support
            - BBR Support
            - LZ4KD Support
"""

JOB_TEMPLATE = """  {job_id}:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        include:
{matrix_entries
    steps:
      - name: Maximize build space
        uses: AdityaGarg8/remove-unwanted-software@v5
        with:
          remove-dotnet: 'true'
          remove-android: 'true'
          remove-haskell: 'true'
          remove-codeql: 'true'
          remove-docker-images: 'true'
          remove-large-packages: 'true'
          remove-swapfile: 'true'
          verbose: 'true'

      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: |
          sudo apt update && sudo apt upgrade -y
          sudo apt install -y ccache python3 git curl wget zip unzip
          pip install PyYAML

      - name: Configure ccache
        run: |
          mkdir -p ~/.cache/bazel
          ccache --version
          ccache --max-size=2G
          ccache --set-config=compression=true
          echo "CCACHE_DIR=$HOME/.ccache" >> $GITHUB_ENV

      - name: Build {display_name}
        run: |
          cd ./.github/workflows
          ARGS="--android {android} --kernel {kernel} --sub-level ${{ matrix.sub_level }} --os-patch ${{ matrix.os_patch_level }} --ksu-version ${{ env.KSU_VERSION }} --no-release"
          [ "${{ env.USE_ZRAM }}" = "true" ] && ARGS="$ARGS --zram"
          [ "${{ env.USE_KPM }}" = "false" ] && ARGS="$ARGS --no-kpm"
          [ "${{ env.USE_BBG }}" = "true" ] && ARGS="$ARGS --bbg"
          [ -n "${{ env.KSU_COMMIT }}" ] && ARGS="$ARGS --ksu-commit ${{ env.KSU_COMMIT }}"
          [ -n "${{ env.SUSFS_COMMIT }}" ] && ARGS="$ARGS --susfs-commit ${{ env.SUSFS_COMMIT }}"
          [ -n "${{ env.CUSTOM_VERSION }}" ] && ARGS="$ARGS --version ${{ env.CUSTOM_VERSION }}"
          python3 build.py $ARGS

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: kernel-{job_id}-${{ matrix.sub_level }}
          path: |
            *.zip
            *.img
"""


def generate_matrix_entry(entry: dict) -> str:
    """生成单个 matrix entry"""
    lines = [f"          - sub_level: \"{entry['sub_level']}\""]
    lines.append(f"            os_patch_level: \"{entry['os_patch_level']}\"")
    if "revision" in entry and entry["revision"]:
        lines.append(f"            revision: \"{entry['revision']}\"")
    return "\n".join(lines)


def generate_job(android: str, kernel: str, entries: list) -> str:
    """生成单个 job"""
    job_id = f"build-{android}-{kernel.replace('.', '-')}"
    display_name = f"{android} {kernel}"
    
    matrix_entries = "\n".join(generate_matrix_entry(e) for e in entries)
    
    return JOB_TEMPLATE.format(
        job_id=job_id,
        display_name=display_name,
        android=android,
        kernel=kernel,
        matrix_entries=matrix_entries,
    )


def generate_workflow(matrix: dict) -> str:
    """生成完整的 workflow"""
    jobs = []
    job_names = []
    
    # 按版本排序
    for key in sorted(matrix.keys()):
        android, kernel = key.split("-", 1)
        job_id = f"build-{android}-{kernel.replace('.', '-')}"
        job_names.append(job_id)
        
        entries = matrix[key]
        job_content = generate_job(android, kernel, entries)
        jobs.append(job_content)
    
    return TEMPLATE.format(
        matrix_jobs="\n\n".join(jobs),
        job_names=", ".join(job_names),
    )


def main():
    # 读取 matrix.json
    script_dir = Path(__file__).parent
    matrix_file = script_dir / "matrix.json"
    
    if not matrix_file.exists():
        print(f"Error: {matrix_file} not found", file=sys.stderr)
        sys.exit(1)
    
    with open(matrix_file, "r", encoding="utf-8") as f:
        matrix = json.load(f)
    
    # 生成 workflow
    workflow = generate_workflow(matrix)
    
    # 输出到 build-all-kernels.yml
    output_file = script_dir / "build-all-kernels.yml"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(workflow)
    
    print(f"Generated: {output_file}")
    
    # 统计
    total = sum(len(v) for v in matrix.values())
    print(f"Total configurations: {total}")
    for key in sorted(matrix.keys()):
        print(f"  {key}: {len(matrix[key])} configs")


if __name__ == "__main__":
    main()
