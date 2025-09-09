import json
import base64
import re
import urllib.parse

# ========== 固定参数 ==========
UUID = "bc9ed311-58bf-4c13-89f9-8e7e0004e58d"
WORKER_DOMAIN = "e194.yuba.ddns-ip.net"   # 你自己的workers域名/自定义域名
PATH = "/?ed=2560"
NO_TLS_PORTS = {"8080", "80", "8880", "2052", "2082", "2086"}

# ========== KV 数据，可以改成从文件读取 ==========
kv_data = {
    "node1": "www.visa.com.sg",
    "node2": "cis.visa.com",
    "node3": "1.2.3.4",
    "node4": "5.6.7.8:8080"
}

# ========== 拼接逻辑 ==========
def generate_vless(name, value):
    nodes = []

    # 判断是否是 IP
    is_ip = re.match(r"^\d+\.\d+\.\d+\.\d+(?::\d+)?$", value)
    host = WORKER_DOMAIN
    path_enc = urllib.parse.quote(PATH, safe="")

    if is_ip:
        # 拆分 IP + 端口
        parts = value.split(":")
        ip = parts[0]
        port = parts[1] if len(parts) > 1 else None

        if not port:
            # 裸 IP -> 默认443 + TLS
            nodes.append(
                f"vless://{UUID}@{ip}:443?encryption=none&security=tls&sni={host}&fp=random&type=ws&host={host}&path={path_enc}#{name}"
            )
        elif port in NO_TLS_PORTS:
            # 特殊端口 -> 无TLS
            nodes.append(
                f"vless://{UUID}@{ip}:{port}?encryption=none&security=none&fp=randomized&type=ws&host={host}&path={path_enc}#{name}"
            )
    else:
        # 域名 -> 生成两种
        nodes.append(
            f"vless://{UUID}@{value}:443?encryption=none&security=tls&sni={host}&fp=random&type=ws&host={host}&path={path_enc}#{name}"
        )
        nodes.append(
            f"vless://{UUID}@{value}:8080?encryption=none&security=none&fp=randomized&type=ws&host={host}&path={path_enc}#{name}"
        )

    return nodes


# ========== 执行拼接 ==========
all_nodes = []
for k, v in kv_data.items():
    all_nodes.extend(generate_vless(k, v))

# 明文输出
with open("nodes.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(all_nodes))

# Base64 订阅输出
sub_content = base64.b64encode("\n".join(all_nodes).encode()).decode()
with open("nodes_sub.txt", "w", encoding="utf-8") as f:
    f.write(sub_content)

print("生成完成：nodes.txt（明文） 和 nodes_sub.txt（订阅）")
