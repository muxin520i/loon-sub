#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clash YAML -> Loon 可用的节点订阅（标准 URI 列表 + Base64）
用法: python3 clash2loon.py input.yaml outdir
"""
import base64
import json
import os
import sys
import urllib.parse as up

import yaml

# Loon 不支持的传输层（Xray 的 xhttp / splithttp），直接跳过
UNSUPPORTED_NET = {"xhttp", "splithttp", "grpc", "kcp"}


def q(d):
    """按 dict 顺序拼 query，空值丢弃"""
    pairs = []
    for k, v in d.items():
        if v is None or v == "":
            continue
        pairs.append(f"{k}={up.quote(str(v), safe='')}")
    return "&".join(pairs)


def tag(name):
    return up.quote(name, safe="")


def ws_path(net_opts):
    p = net_opts.get("path")
    if isinstance(p, list):
        p = p[0] if p else ""
    return p or "/"


def ws_host(net_opts, fallback=""):
    h = net_opts.get("headers", {}).get("Host")
    if isinstance(h, list):
        h = h[0] if h else None
    return h or fallback


def to_ss(p):
    userinfo = f"{p['cipher']}:{p['password']}"
    b = base64.urlsafe_b64encode(userinfo.encode()).decode().rstrip("=")
    return f"ss://{b}@{p['server']}:{p['port']}#{tag(p['name'])}"


def to_vmess(p):
    net = p.get("network") or "tcp"
    opts = p.get("ws-opts" if net == "ws" else ("h2-opts" if net in ("h2", "http") else "http-opts")) or {}
    if net in ("h2", "http"):
        net = "h2"
    host = ws_host(opts) or p.get("servername") or p.get("sni") or ""
    obj = {
        "v": "2",
        "ps": p["name"],
        "add": p["server"],
        "port": str(p["port"]),
        "id": p["uuid"],
        "aid": str(p.get("alterId", 0)),
        "scy": p.get("cipher", "auto"),
        "net": net,
        "type": "none",
        "host": host,
        "path": ws_path(opts),
        "tls": "tls" if p.get("tls") else "",
        "sni": p.get("servername") or p.get("sni") or "",
        "alpn": ",".join([a for a in (p.get("alpn") or []) if a]),
        "fp": p.get("client-fingerprint", ""),
    }
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return "vmess://" + base64.b64encode(raw.encode()).decode()


def to_vless(p):
    net = p.get("network") or "tcp"
    opts = p.get("ws-opts" if net == "ws" else ("h2-opts" if net in ("h2", "http") else "grpc-opts")) or {}
    if net in ("h2", "http"):
        net = "h2"
    reality = p.get("reality-opts") or {}
    params = {"encryption": p.get("encryption") or "none", "type": net}

    if reality:
        params.update({
            "security": "reality",
            "sni": p.get("servername") or p.get("sni") or "",
            "fp": p.get("client-fingerprint") or "chrome",
            "pbk": reality.get("public-key", ""),
            "sid": reality.get("short-id", ""),
        })
    elif p.get("tls"):
        params.update({
            "security": "tls",
            "sni": p.get("servername") or p.get("sni") or "",
            "fp": p.get("client-fingerprint") or "",
            "alpn": ",".join([a for a in (p.get("alpn") or []) if a]),
            "allowInsecure": "1" if p.get("skip-cert-verify") else "0",
        })
    else:
        params.update({"security": "none", "allowInsecure": "1" if p.get("skip-cert-verify") else "0"})

    if p.get("flow"):
        params["flow"] = p["flow"]
    if net == "ws":
        params["host"] = ws_host(opts, p.get("servername") or "")
        params["path"] = ws_path(opts)
    elif net == "h2":
        params["host"] = ws_host(opts, p.get("servername") or "")
        params["path"] = ws_path(opts)
    elif net == "grpc":
        params["serviceName"] = opts.get("grpc-service-name", "")

    return f"vless://{p['uuid']}@{p['server']}:{p['port']}?{q(params)}#{tag(p['name'])}"


def to_trojan(p):
    net = p.get("network") or "tcp"
    opts = p.get("ws-opts") or {}
    params = {"security": "tls", "sni": p.get("sni") or p.get("servername") or "", "type": net}
    if net == "ws":
        params["host"] = ws_host(opts, p.get("sni") or "")
        params["path"] = ws_path(opts)
    if p.get("alpn"):
        params["alpn"] = ",".join([a for a in p["alpn"] if a])
    if p.get("skip-cert-verify"):
        params["allowInsecure"] = "1"
    return f"trojan://{up.quote(str(p['password']), safe='')}@{p['server']}:{p['port']}?{q(params)}#{tag(p['name'])}"


BUILDERS = {"ss": to_ss, "vmess": to_vmess, "vless": to_vless, "trojan": to_trojan}


def main(src, outdir):
    d = yaml.safe_load(open(src, encoding="utf-8"))
    uris, skipped, seen = [], [], set()

    for p in d.get("proxies", []):
        name, typ = p.get("name", ""), p.get("type")
        net = (p.get("network") or "tcp").lower()
        if typ not in BUILDERS:
            skipped.append((name, f"不支持的协议 {typ}"))
            continue
        if net in UNSUPPORTED_NET and typ != "ss":
            skipped.append((name, f"Loon 不支持 {net} 传输"))
            continue
        enc = str(p.get("encryption") or "none")
        if typ == "vless" and enc not in ("none", ""):
            skipped.append((name, "使用了新版 VLESS 加密，Loon 不支持"))
            continue
        try:
            uri = BUILDERS[typ](p)
        except Exception as e:  # noqa
            skipped.append((name, f"转换失败 {e}"))
            continue
        if uri in seen:
            skipped.append((name, "重复节点"))
            continue
        seen.add(uri)
        uris.append(uri)

    body = "\n".join(uris) + "\n"
    os.makedirs(outdir, exist_ok=True)

    with open(os.path.join(outdir, "nodes.txt"), "w", encoding="utf-8") as f:
        f.write(body)
    with open(os.path.join(outdir, "sub.txt"), "w", encoding="utf-8") as f:
        f.write(base64.b64encode(body.encode()).decode())

    print(f"转换成功: {len(uris)} 个节点")
    print(f"跳过: {len(skipped)} 个")
    for n, r in skipped:
        print(f"  - {n}  <-- {r}")
    return len(uris), skipped


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
