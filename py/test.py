import os
import base64
import re
import urllib.parse
import yaml

# ========== 固定参数 ==========
UUID = "bc9ed311-58bf-4c13-89f9-8e7e0004e58d"
WORKER_DOMAIN = "e194.yubo220.workers.dev"  # 你的 Worker 域名
PATH = "/?ed=2560"
NO_TLS_PORTS = {"8080", "80", "8880", "2052", "2082", "2086"}

# ========== 文件路径 ==========
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_FILE = os.path.join(BASE_DIR, "py", "nodes.txt")
OUTPUT_DIR = os.path.join(BASE_DIR, "test")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "nodes.txt")
OUTPUT_SUB_FILE = os.path.join(OUTPUT_DIR, "nodes_sub.txt")
OUTPUT_CLASH_FILE = os.path.join(OUTPUT_DIR, "nodes_clash.yaml")

# ========== 节点拼接函数 ==========
def generate_vless(name, value):
    nodes = []
    is_ip = re.match(r"^\d+\.\d+\.\d+\.\d+(?::\d+)?$", value)
    host = WORKER_DOMAIN
    path_enc = urllib.parse.quote(PATH, safe="")

    if is_ip:
        parts = value.split(":")
        ip = parts[0]
        port = parts[1] if len(parts) > 1 else None

        if not port:
            nodes.append({
                "name": name,
                "server": ip,
                "port": 443,
                "type": "vless",
                "uuid": UUID,
                "tls": True,
                "network": "ws",
                "ws-opts": {"path": PATH, "headers": {"Host": host}},
                "udp": True
            })
        elif port in NO_TLS_PORTS:
            nodes.append({
                "name": name,
                "server": ip,
                "port": int(port),
                "type": "vless",
                "uuid": UUID,
                "tls": False,
                "network": "ws",
                "ws-opts": {"path": PATH, "headers": {"Host": host}},
                "udp": True
            })
    else:
        # 域名 → 两种
        nodes.append({
            "name": f"{name}_tls",
            "server": value,
            "port": 443,
            "type": "vless",
            "uuid": UUID,
            "tls": True,
            "network": "ws",
            "ws-opts": {"path": PATH, "headers": {"Host": host}},
            "udp": True
        })
        nodes.append({
            "name": f"{name}_notls",
            "server": value,
            "port": 8080,
            "type": "vless",
            "uuid": UUID,
            "tls": False,
            "network": "ws",
            "ws-opts": {"path": PATH, "headers": {"Host": host}},
            "udp": True
        })
    return nodes

# ========== 读取 nodes.txt（支持路径引用） ==========
def load_nodes(file_path):
    nodes = {}
    if not os.path.exists(file_path):
        print(f"❌ 找不到文件: {file_path}")
        return nodes

    with open(file_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # 如果是文件路径，读取子文件
            if os.path.isfile(os.path.join(BASE_DIR, line)):
                sub_file = os.path.join(BASE_DIR, line)
                with open(sub_file, "r", encoding="utf-8") as sf:
                    for sub_idx, sub_line in enumerate(sf, 1):
                        sub_line = sub_line.strip()
                        if sub_line and not sub_line.startswith("#"):
                            nodes[f"{os.path.basename(sub_file)}_{sub_idx}"] = sub_line
            else:
                nodes[f"node{idx}"] = line
    return nodes

# ========== 主程序 ==========
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    kv_data = load_nodes(INPUT_FILE)

    all_nodes_vless = []
    all_nodes_clash = []

    for k, v in kv_data.items():
        nodes = generate_vless(k, v)
        all_nodes_clash.extend(nodes)

        # 转换成 vless:// 链接
        for n in nodes:
            tls_part = "tls" if n.get("tls") else "none"
            port = n["port"]
            server = n["server"]
            name = n["name"]
            host = n["ws-opts"]["headers"]["Host"]
            path = urllib.parse.quote(n["ws-opts"]["path"], safe="")
            all_nodes_vless.append(
                f"vless://{UUID}@{server}:{port}?encryption=none&security={'tls' if n['tls'] else 'none'}"
                f"{'&sni=' + host if n['tls'] else ''}"
                f"&fp=random&type=ws&host={host}&path={path}#{name}"
            )

    # ======= 输出明文和 base64 订阅 =======
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(all_nodes_vless))

    sub_content = base64.b64encode("\n".join(all_nodes_vless).encode()).decode()
    with open(OUTPUT_SUB_FILE, "w", encoding="utf-8") as f:
        f.write(sub_content)

    # ======= 生成 Clash Meta YAML (方案1) =======
    clash_config = {
        "port": 7890,
        "socks-port": 7891,
        "allow-lan": True,
        "mode": "Rule",
        "log-level": "info",
        "proxies": all_nodes_clash,
        "proxy-groups": [
            {
                "name": "🚀 节点选择",
                "type": "select",
                "proxies": [n["name"] for n in all_nodes_clash] + ["DIRECT"]
            },
            {
                "name": "♻️ 自动选择",
                "type": "url-test",
                "url": "http://www.gstatic.com/generate_204",
                "interval": 300,
                "proxies": [n["name"] for n in all_nodes_clash]
            }
        ],
        # 方案1：直接引用 ACL4SSR 在线规则
        "proxy-providers": {
            "mysub": {
                "type": "http",
                "url": "https://raw.githubusercontent.com/qunhui201/free/main/test/nodes_clash.yaml",
                "interval": 3600
            }
        },
        "rule-providers": {
            "ACL4SSR": {
                "type": "http",
                "behavior": "classical",
                "url": "https://raw.githubusercontent.com/zsokami/ACL4SSR/main/ACL4SSR_Online_Full_Mannix.ini",
                "path": "./ruleset/ACL4SSR.ini",
                "interval": 86400
            }
        },
        "rules": [
            "RULE-SET,ACL4SSR,🚀 节点选择",
            "MATCH,DIRECT"
        ]
    }

    with open(OUTPUT_CLASH_FILE, "w", encoding="utf-8") as f:
        yaml.dump(clash_config, f, allow_unicode=True, sort_keys=False)

    print(f"✅ 生成完成: \n - {OUTPUT_FILE}\n - {OUTPUT_SUB_FILE}\n - {OUTPUT_CLASH_FILE}")


if __name__ == "__main__":
    main()
