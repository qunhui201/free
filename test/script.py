import requests
import base64
import yaml
import socket
import json
from urllib.parse import urlparse
from typing import List, Dict, Set

# List of unique URLs provided by the user
URLS = [
    "https://raw.githubusercontent.com/free-nodes/v2rayfree/main/v2",
    "https://raw.githubusercontent.com/free18/v2ray/refs/heads/main/c.yaml",
    "https://raw.githubusercontent.com/Pawdroid/Free-servers/main/sub",
    "https://raw.githubusercontent.com/WLget/V2Ray_configs_64/refs/heads/master/ConfigSub_list.txt",
    "https://raw.githubusercontent.com/ssrsub/ssr/master/v2ray",
    "https://raw.githubusercontent.com/StormragerCN/v2ray/raw/refs/heads/main/v2ray",
    "https://raw.githubusercontent.com/aiboboxx/clash/main/free",
    "https://raw.githubusercontent.com/MZF0121/fanqiang/master/v2ray",
    "https://raw.githubusercontent.com/leetomlee123/freenode/main/v2ray",
    "https://www.xrayvip.com/free.txt",
    "https://raw.githubusercontent.com/nodesfree/v2raynode/main/sub",
    "https://raw.githubusercontent.com/shaoyouvip/free/main/v2ray",
    "https://raw.githubusercontent.com/jiawe1258/V2Ray_-/main/v2ray",
    "https://raw.githubusercontent.com/freefq/free/master/v2",
    "https://raw.githubusercontent.com/liuxu0511/free18-v2ray/main/c.yaml",
    "https://raw.githubusercontent.com/sun9426/sun9426.github.io/main/v2ray",
    "https://raw.githubusercontent.com/hwanz/SSR-V2ray-Trojan-vpn/main/sub",
    "https://raw.githubusercontent.com/mack-a/v2ray-agent/master/sub.txt",
    "https://raw.githubusercontent.com/v2raynode/v2raynode/main/free.txt",
    "https://raw.githubusercontent.com/freeclashnode/free/main/clash.yaml",
    "https://raw.githubusercontent.com/v2rayse/free/main/v2ray.txt",
    "https://raw.githubusercontent.com/wanzhuanmi/free/main/clash.yaml",
    "https://raw.githubusercontent.com/cfmem/free/main/v2ray",
    "https://raw.githubusercontent.com/mibei77/free/main/v2ray.txt",
    "https://raw.githubusercontent.com/clashgithub/free/main/clash.yaml",
    "https://raw.githubusercontent.com/v2raynode/free/main/v2ray",
    "https://raw.githubusercontent.com/free18/free/main/v2ray.txt",
    "https://raw.githubusercontent.com/Pawdroid/Free-servers/main/v2ray",
    "https://raw.githubusercontent.com/nodesfree/free/main/clash.yaml",
    "https://raw.githubusercontent.com/sharmajv/vpn/main/free.txt"
]

# Function to download content from a URL
def download_content(url: str) -> str:
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text.strip()
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return ""

# Function to parse base64 encoded content (common for V2Ray/SSR subscriptions)
def parse_base64_content(content: str) -> List[str]:
    try:
        decoded = base64.b64decode(content).decode('utf-8').strip()
        return decoded.splitlines()
    except:
        return []

# Function to parse YAML content (for Clash configs)
def parse_yaml_content(content: str) -> List[Dict]:
    try:
        data = yaml.safe_load(content)
        if 'proxies' in data:
            return data['proxies']
        return []
    except:
        return []

# Function to parse plain text lines (e.g., lists of links or configs)
def parse_plain_text(content: str) -> List[str]:
    return content.splitlines()

# Function to extract node info based on format
def extract_nodes(url: str, content: str) -> List[Dict]:
    nodes = []
    format_type = "unknown"
    
    if url.endswith('.yaml') or 'clash' in url.lower():
        format_type = "yaml"
        proxies = parse_yaml_content(content)
        for proxy in proxies:
            node = {
                'type': proxy.get('type', 'unknown'),
                'server': proxy.get('server'),
                'port': proxy.get('port'),
                'full_config': json.dumps(proxy, sort_keys=True)  # For dedup
            }
            nodes.append(node)
    
    elif 'base64' in content.lower() or len(content) % 4 == 0:  # Heuristic for base64
        format_type = "base64"
        lines = parse_base64_content(content)
        for line in lines:
            if line.startswith(('vmess://', 'ss://', 'trojan://', 'ssr://')):
                parsed = parse_proxy_link(line)
                if parsed:
                    nodes.append(parsed)
    
    else:
        format_type = "plain"
        lines = parse_plain_text(content)
        for line in lines:
            if line.startswith(('vmess://', 'ss://', 'trojan://', 'ssr://')):
                parsed = parse_proxy_link(line)
                if parsed:
                    nodes.append(parsed)
    
    print(f"Extracted {len(nodes)} nodes from {url} (format: {format_type})")
    return nodes

# Simple parser for common proxy links
def parse_proxy_link(link: str) -> Dict:
    try:
        scheme = urlparse(link).scheme
        if scheme == 'vmess':
            # vmess://base64(json)
            encoded = link.split('://')[1]
            decoded = base64.b64decode(encoded + '==').decode('utf-8')  # Padding if needed
            config = json.loads(decoded)
            return {
                'type': 'vmess',
                'server': config.get('add'),
                'port': config.get('port'),
                'full_config': link
            }
        elif scheme == 'ss':
            # ss://base64(method:password)@server:port
            parts = link.split('://')[1].split('@')
            auth = base64.b64decode(parts[0] + '==').decode('utf-8')
            server_port = parts[1].split(':')
            return {
                'type': 'ss',
                'server': server_port[0],
                'port': int(server_port[1].split('#')[0]),
                'full_config': link
            }
        elif scheme == 'trojan':
            # trojan://password@server:port
            parts = link.split('://')[1].split('@')
            password = parts[0]
            server_port = parts[1].split(':')
            return {
                'type': 'trojan',
                'server': server_port[0],
                'port': int(server_port[1].split('?')[0].split('#')[0]),
                'full_config': link
            }
        elif scheme == 'ssr':
            # ssr://base64(config)
            encoded = link.split('://')[1]
            decoded = base64.b64decode(encoded + '==').decode('utf-8')
            parts = decoded.split(':')
            return {
                'type': 'ssr',
                'server': parts[0],
                'port': int(parts[1]),
                'full_config': link
            }
        return None
    except:
        return None

# Function to deduplicate nodes based on full_config
def deduplicate_nodes(all_nodes: List[Dict]) -> List[Dict]:
    seen: Set[str] = set()
    unique_nodes = []
    for node in all_nodes:
        config_str = node['full_config']
        if config_str not in seen:
            seen.add(config_str)
            unique_nodes.append(node)
    print(f"Deduplicated to {len(unique_nodes)} unique nodes")
    return unique_nodes

# Function to test connectivity (simple port check)
def test_connectivity(node: Dict) -> bool:
    if not node.get('server') or not node.get('port'):
        return False
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((node['server'], int(node['port'])))
        sock.close()
        return result == 0
    except:
        return False

# Main function
def main():
    all_nodes = []
    for url in URLS:
        content = download_content(url)
        if content:
            nodes = extract_nodes(url, content)
            all_nodes.extend(nodes)
    
    unique_nodes = deduplicate_nodes(all_nodes)
    
    working_nodes = []
    for node in unique_nodes:
        if test_connectivity(node):
            working_nodes.append(node)
            print(f"Working node: {node['type']} - {node['server']}:{node['port']}")
    
    print(f"Total working nodes: {len(working_nodes)}")
    
    # Output working nodes to a file (e.g., for GitHub Actions artifact)
    with open('working_nodes.json', 'w') as f:
        json.dump(working_nodes, f, indent=4)

if __name__ == "__main__":
    main()
