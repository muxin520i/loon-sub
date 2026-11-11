# Loon 订阅（Clash YAML → Loon 转换）

把 `clash.yaml` 里的 55 个节点转成 Loon 可直接「添加订阅」的格式，剔除 Loon 不支持的传输方式后，**41 个节点可用**。

## 订阅链接

```
https://raw.githubusercontent.com/muxin520i/loon-sub/main/sub.txt
```

国内直连不稳时用加速镜像（任选其一，内容相同）：

```
https://cdn.jsdelivr.net/gh/muxin520i/loon-sub@main/sub.txt
https://ghfast.top/https://raw.githubusercontent.com/muxin520i/loon-sub/main/sub.txt
```

## 在 Loon 里添加

1. 复制上面的订阅链接
2. Loon 首页底部点 **配置** → 右上角 **＋** → **添加订阅**
   （也可以：首页 → 左上 `LOON` 旁边的设置 → 节点 → 添加订阅）
3. **URL** 粘贴订阅链接，**别名**随便填（如 `节点池`）
4. 右上角 **✓** 保存 → 节点列表会自动拉取，下拉可刷新

> 「添加订阅」只导入节点，不含分流规则。原 yaml 里的 `AI-POOL / PROXY` 策略组和 openai/claude 规则，需要在 Loon 的「配置」里另外添加，或直接用 Loon 自带规则集。

## 文件说明

| 文件 | 用途 |
| --- | --- |
| `sub.txt` | Base64 编码的节点列表，**订阅链接用这个** |
| `nodes.txt` | 明文节点列表，可手动全选复制 → Loon「从剪贴板导入」 |
| `clash2loon.py` | 转换脚本，源 yaml 更新后重新生成 |

## 节点构成

| 协议 | 数量 | 说明 |
| --- | --- | --- |
| VLESS | 25 | 含 7 个 REALITY（tcp + vision）、18 个 WS/TCP + TLS |
| Shadowsocks | 11 | 10 个 `aes-256-gcm` + 1 个 `aes-256-cfb` |
| VMess | 4 | WS 3 个 + h2 1 个 |
| Trojan | 1 | WS + TLS |

## 已知限制（原 yaml 里有、Loon 用不了）

14 个节点使用 Xray 的 `xhttp` 传输，Loon 不支持该协议，已跳过：

- 🇸🇬 新加坡 | SGP 2
- 🇺🇸 美国 | USA 6 / USA 7
- 🇳🇱 荷兰 | NLD
- 🇨🇦 加拿大 | CAN
- 🇩🇪 德国 | DEU 6 / DEU 8
- 🇵🇱 波兰 | POL / POL 2
- 🇫🇷 法国 | FRA 3 / FRA 4 / FRA 8
- 🇪🇸 西班牙 | ESP
- ❓未知丨yoyapai.com (21)

另外：

- `🇺🇸 美国 | USA 4` 用的是 `aes-256-cfb`，Loon 新版可能已移除该旧加密，导入后若连不上属正常。
- `🇭🇰 香港 | HKG 2` 是 VMess + h2，部分 Loon 版本不支持 VMess 的 h2 传输。

## 更新节点

```bash
python3 clash2loon.py clash.yaml .
git add -A && git commit -m "update nodes" && git push
```

Loon 端下拉刷新即可生效。
