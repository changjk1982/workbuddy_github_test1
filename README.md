# workbuddy_github_test1

嘉立创EDA 专业版（LCEDA Pro）工程仓库 —— 用于验证「本地工作区 ↔ github.com 远端」的版本控制与备份链路。

## 用途

本仓库是链路打通后的首个测试工程，验证三件事：

1. 本地 git 能连通 `github.com`（曾有两层障碍：`.gitconfig` 中的 `insteadOf` 重写规则、以及 Steam++ 的本地 TLS 中间人，均已解决 —— 详见 [`docs/github-tls-mitm-troubleshooting.md`](docs/github-tls-mitm-troubleshooting.md)）
2. 工程源文件可正常提交并推送到远端仓库
3. `.gitignore` 规则能正确把 EDA 的 `_tmp/` 与缓存目录挡在版本控制之外

## 约定的版本控制原则

只跟踪**不可再生的设计意图**，排除**可随时重新生成的产物**：

| 入库 | 不入库 |
|---|---|
| 原理图、PCB、符号、封装 | `_tmp/`、缓存目录 |
| 手工维护的 BOM（含选型/替代料决策） | 自动生成的网表 `*.net` |
| 固件源码、测试脚本 | gerber / 钻孔 / 坐标文件 |
| 设计说明文档 | 自动保存快照 `*.autosave`、`*.bak` |

判定标准、宽泛通配符的误伤风险及排查命令，见 `.gitignore` 文件末尾的说明。

## 目录结构

```
workbuddy_github_test1/
├── .gitignore        排除规则（含判定标准与排查方法）
├── .gitattributes    行尾符与二进制处理策略
├── docs/
│   └── github-tls-mitm-troubleshooting.md   GitHub 访问故障排查记录
├── hardware/
│   └── STM32F103C8T6-MinSys/                STM32F103C8T6 最小系统板（详见该目录 README）
│       ├── STM32F103C8T6-MinSys.epro2       工程源文件（原理图 + PCB）
│       ├── BOM/                             物料清单
│       ├── images/                          原理图 / PCB 预览
│       └── README.md                        硬件设计说明
├── tools/
│   ├── epro_parse.py                        .epro2 工程文件解析器
│   └── gen_bom.py                           从工程文件离线生成 BOM
└── README.md         本文件
```

## 工程内容

### `hardware/STM32F103C8T6-MinSys` —— STM32F103C8T6 最小系统板

| 项目 | 参数 |
|---|---|
| 主控 | STM32F103C8T6（LQFP-48） |
| 供电 | USB Type-C 5V → AMS1117-3.3 → 3.3V |
| 时钟 | 8MHz 无源晶振 |
| 板框 | 45.72 × 31.75 mm |
| 元件 | 25 个（14 种物料） |
| 状态 | 原理图完成（ERC 0 错误）；PCB 已完成布局/板框/安装孔/Mark 点，**布线待完成** |

详细设计说明、网表、PCB 参数见 [`hardware/STM32F103C8T6-MinSys/README.md`](hardware/STM32F103C8T6-MinSys/README.md)。

## 环境依赖（本机）

| 组件 | 版本/路径 |
|---|---|
| git | `D:\Program Files\Git\cmd\git.exe`（2.43.0.windows.1） |
| 默认分支 | `main` |
| 远端 | `git@github.com` → 实际使用 HTTPS + Git Credential Manager |
| 嘉立创EDA 专业版 | `E:\Program Files\lceda-pro\` |

## 常用操作

```bash
# 提交并推送
git add -A && git commit -m "描述本次改动" && git push

# 确认某个文件是被哪条规则排除的（排查"文件莫名不见"用这个）
git check-ignore -v <文件路径>

# 查看远端
git remote -v
```

## 关联

- 嘉立创EDA 与 WorkBuddy 的桥接环境运维方法，见本地 skill `easyeda-pro-bridge-ops`
- Bridge Server 启停脚本位于上级目录：`F:\EDA_JLC\eda-bridge-start.cmd` / `eda-bridge-stop.cmd`
