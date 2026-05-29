# GKI KernelSU + SUSFS 构建系统

### 这是一个现代化自动构建 GKI 内核的仓库

> 非 GKI 可以尝试 [SukiSU 云盘](https://alist.shirkneko.top) 的资源，不支持一加 ColorOS14、15

> 第一次使用务必 **详细阅读** 以下内容，不要因为懒惰而占用他人时间！

> 使用 Python 构建系统，支持指定 KernelSU/SUSFS commit 版本构建


---

## 快速开始

### GitHub Actions

#### 方式一：构建单个版本
1. 进入 **Actions** 页面
2. 选择 **GKI Kernel Build**
3. 点击 **Run workflow**
4. 选择 Android 版本、Kernel 版本和构建选项
5. 可选：指定 KernelSU 或 SUSFS 的 commit hash

#### 方式二：构建所有版本
1. 选择 **Build All Kernels**
2. 点击 **Run workflow**
3. 设置全局选项（KSU 版本、ZRAM、KPM 等）
4. 可选：指定 commit 版本

### 命令行本地构建

```bash
# 进入构建目录
cd .github/workflows

# 安装依赖
pip install -r requirements.txt

# 构建单个版本
python build.py --android android14 --kernel 6.1 --sub-level 124 --os-patch 2025-02

# 构建整个矩阵
python build.py --matrix android14-6.1

# 构建所有版本
python build.py --all

# 指定 commit 版本
python build.py --all --ksu-commit abc1234 --susfs-commit HEAD~1
```

---

## 构建矩阵

从 `matrix.json` 加载：

| Android | Kernel | Sub Levels |
|---------|--------|------------|
| 12 | 5.10 | 136, 198, 209, 236, X (LTS) |
| 13 | 5.10 | X (LTS) |
| 13 | 5.15 | 74, 123, 148, 170, 178, 180, 189 |
| 14 | 5.15 | X (LTS) |
| 14 | 6.1 | 78, 90, 99, 124, 145 |
| 15 | 6.6 | 50, 66, 102 |

总计 **19 个版本组合**

---

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--android, -a` | Android 版本 | android14 |
| `--kernel, -k` | Kernel 版本 | 6.1 |
| `--sub-level, -s` | Sub level 版本 | 124 |
| `--os-patch` | OS Patch Level | 2025-02 |
| `--ksu-version` | KernelSU 版本 | Stable(标准) |
| `--ksu-commit` | 指定 KernelSU commit hash | latest |
| `--susfs-commit` | 指定 SUSFS commit (hash 或 HEAD~N) | latest |
| `--no-zram` | 禁用 ZRAM (LZ4KD) | False |
| `--no-kpm` | 禁用 KPM | False |
| `--bbg` | 启用 Baseband-guard | False |
| `--op8e` | 启用 OnePlus 8E 支持 | False |
| `--bbr` | 设置 BBR 为默认拥塞算法 | False |
| `--matrix, -m` | 使用预定义矩阵 | - |
| `--all` | 构建所有配置 | - |
| `--list-matrix` | 列出所有预定义矩阵 | - |
| `--dry-run` | 仅验证配置 | - |

---

## 下载

可以 [在此](https://github.com/zzh20188/GKI_KernelSU_SUSFS/releases) 下载您的资源

1. **AnyKernel3.zip** - 下载即用！
   - 使用刷入软件，例如 [HorizonKernelFlasher](https://github.com/libxzr/HorizonKernelFlasher/releases) 进行刷写内核

2. **boot.img** - 下载与你内核格式相匹配的（无压缩、gz、lz4）
   - 使用 [FASTBOOT](https://magiskcn.com/) 刷入

---

## 支持的功能

| 功能 | 说明 |
|------|------|
| [KernelSU](https://kernelsu.org/zh_CN/) | SukiSU 内核Root方案 |
| [SUSFS4](https://gitlab.com/simonpunk/susfs4ksu) | 内核层面辅助 KSU 隐藏的功能补丁 |
| [BBR](https://blog.thinkin.top/archives/ke-pu-bbrdao-di-shi-shi-me) | TCP 拥塞控制算法 |
| [LZ4KD](https://github.com/ShirkNeko/SukiSU_patch/tree/main/other) | 来自华为源码的 ZRAM 算法 |

<details>

<summary>支持的 ZRAM 算法（可在 Scene 切换）</summary>

LZ4K、LZ4HC、deflate、842、lz4k_oplus

</details>

---

## KSU 管理器

在编译完成后，会生成最新的管理器 APK。

---

## 紧急救援指南

> **触发条件**
> 当设备因刷入错误/不兼容的内核无法启动时需执行救援

1. 进入 FASTBOOT 模式
   - 物理键组合：电源+音量-
   - 或 ADB 命令：`adb reboot bootloader`

2. 执行刷写命令
```bash
fastboot flash boot <boot.img文件全称>
```

---

## 内核版本兼容性说明

### 1. 跨子版本刷机规则

当手机 GKI 主版本为 5.10.x 时（如 5.10.168），可刷写同主版本更高子版本的内核（如 5.10.198）。

关于 **X-lts** 版本，以 `android12-5.10.X-lts-AnyKernel3.zip` 为例：
- **X-lts** 表示长期支持版（子版本号最大，当前示例为 5.10.236）
- LTS 随着 GKI 源码更新，编译版本号将持续递增
- ⚠️ 注意：LTS 虽为最新，但最新版 ≠ 最稳定（如 6.6.x 存在自动重启 BUG）

### 2. 内核版本伪装方法

在 MT 管理器终端执行：
```bash
uname -r | sed 's/^[^-]*//'
```
获取后复制版本号，填入 Action 编译面板即可实现内核版本伪装。

### 3. 定制构建矩阵

编辑 `matrix.json` 添加或修改构建版本：
```json
{
  "android14-6.1": [
    {"sub_level": "124", "os_patch_level": "2025-02"},
    {"sub_level": "145", "os_patch_level": "2025-09"}
  ]
}
---

## 更多内容

可以提及您的意见...我会尝试！
