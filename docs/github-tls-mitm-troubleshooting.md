# GitHub 访问故障排查：Steam++ 中间人拦截

> 记录一次 `git push` 与浏览器访问 github.com 同时失败的完整根因定位过程。
> 适用环境：Windows + Git for Windows 2.43（OpenSSL 后端）+ 本机安装 Steam++（Watt Toolkit）。

## 1. 故障现象

同一台机器上出现两个看似无关、实则同源的现象：

| 现象 | 表现 |
|---|---|
| 浏览器 | github.com 网页刷新不出来（连接超时 / 证书错误） |
| `git push` / `ls-remote` | `fatal: unable to access ...: SSL certificate problem: unable to get local issuer certificate` |
| `curl https://github.com` | `schannel: next InitializeSecurityContext failed: Unknown error (0x80092012) - 吊销功能无法检查证书是否吊销` |
| `curl https://api.github.com` | **正常返回 200** |

最后一行是关键线索：同一域名族里只有 `api.github.com` 通，其余全挂——说明问题不在网络出口，而在**本机对该域名的处理链路**。

## 2. 根因

本机安装了 **Steam++（Watt Toolkit，BeyondDimension 出品）**，并开启了「GitHub 加速」。其工作方式是典型的本地中间人：

1. **改写 hosts**：把 `github.com`、`api.github.com`、`*.githubusercontent.com`、`github.io` 等整族域名全部指向 `127.0.0.1`。
   特征：`C:\Windows\System32\drivers\etc\hosts` 末尾有 `# Steam++ End` 标记。

2. **本地代理监听 80/443**：在 `0.0.0.0:80` 与 `0.0.0.0:443` 起监听，接管上述域名，再用**自签根证书**动态签发 `CN=github.com` 的证书给客户端。

3. **证书签发者**：

   ```
   subject=CN=github.com
   issuer =CN=SteamTools Certificate, OU=Technical Department, O=BeyondDimension, C=CN
   ```

因为签发者是自定义 CA，而 Git for Windows 使用 **OpenSSL 后端 + 自带 `ca-bundle.crt`**，该 CA 不在信任列表内，TLS 握手在证书校验阶段直接失败。

curl 走的是 Windows 原生 **schannel** 后端，报错位置不同（卡在 CRL/OCSP 吊销检查 `0x80092012`），但同样是证书链不被认。

**直接结论：这不是 GitHub 的问题，也不是网络出口的问题，是本机 TLS 信任链的问题。**

## 3. 取证命令

```bash
# 1) 确认 hosts 被劫持（看结尾标记）
grep -i github /c/Windows/System32/drivers/etc/hosts

# 2) 确认本地有 80/443 监听
netstat -ano | grep LISTENING | grep -E ":443 |:80 "

# 3) 取出实际收到的证书签发者 —— 这一步直接锁定凶手
openssl s_client -connect github.com:443 -servername github.com -showcerts < /dev/null 2>&1 | grep -E "s:|i:"

# 4) 在 Windows 证书库中定位该根证书
certutil -store Root | grep -i -B1 -A3 "SteamTools"
```

## 4. 修复方案

### 方案 A（推荐，保留加速功能）：把 Steam++ 根证书并入 git 的 CA 包

```bash
# 1) 从 Windows 根证书库导出（DER）
#    用 PowerShell 遍历 LocalMachine\Root 与 CurrentUser\Root，按 Subject 匹配 SteamTools
#    导出为 steamtools_root.cer

# 2) DER -> PEM
openssl x509 -inform DER -in steamtools_root.cer -out steamtools_root.pem

# 3) 与 Git 自带 CA 包合并为超集
cat "/d/Program Files/Git/mingw64/etc/ssl/certs/ca-bundle.crt" \
    steamtools_root.pem > ca-bundle-local.crt

# 4) 让 git 使用该超集包
git config --global http.sslCAInfo "F:/EDA_JLC/.workbuddy/certs/ca-bundle-local.crt"

# 5) 验证
git ls-remote origin
```

本机实际产物：

| 文件 | 说明 |
|---|---|
| `F:\EDA_JLC\.workbuddy\certs\steamtools_root.pem` | 导出的根证书 |
| `F:\EDA_JLC\.workbuddy\certs\ca-bundle-local.crt` | 140 个原有证书 + 1 个 SteamTools 根证书 = 141 |

> 之所以选「超集合并」而不是直接关闭校验：关闭 `http.sslVerify` 会对**所有**仓库永久放弃校验；
> 合并超集则只是把本机自有的 MITM CA 加入白名单，其余证书仍正常校验，安全性不受影响。

### 方案 B（最干净）：退出 Steam++ 的 GitHub 加速

退出后 Steam++ 会自动还原 hosts，`github.com` 解析回真实 IP，git 用自带 CA 包即可正常连接。
代价：在没有其它代理的情况下，浏览器可能重新无法访问 GitHub。

### 回滚

```bash
git config --global --unset http.sslCAInfo
```

## 5. 为什么之前的排查走了弯路

历史上本机 `.gitconfig` 里确实存在一条 `insteadOf` 重写规则，把 `github.com` 劫持向 `jihulab.com`。
该规则**已移除**，但它留下了一个思维惯性：一遇到 GitHub 连不上就先怀疑 git 配置。
本次故障的真实层级在**操作系统 DNS/证书层**，而非 git 配置层。

排查顺序建议固定为：

1. `curl -sk` 能否通 → 区分「网络不通」与「证书不认」
2. 取证书签发者 → 判断是否存在中间人
3. 查 hosts 与本地监听 → 定位中间人身份
4. 最后才查 git 配置

## 6. 验证结果

```
$ git push -u origin main
branch 'main' set up to track 'origin/main'.
To https://github.com/changjk1982/workbuddy_github_test1.git
 * [new branch]      main -> main

$ git log --oneline origin/main
053f145 chore: 初始化嘉立创EDA专业版工程仓库

$ git status -sb
## main...origin/main
```

本地工作区 ↔ github.com 远端链路**已打通**。
