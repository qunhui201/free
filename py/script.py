import requests
import base64
import yaml
import socket
import json
import subprocess
import tempfile
import os
from urllib.parse import urlparse
from typing import List, Dict, Set

# List of URLs that successfully returned nodes
URLS = [
    "https://raw.githubusercontent.com/free18/v2ray/refs/heads/main/v.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-Config/main/Sub1.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-Config/main/Sub2.txt",
    "https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/list_raw.txt",
    "https://raw.githubusercontent.com/ripaojiedian/freenode/main/sub",
    "https://raw.githubusercontent.com/mfuu/v2ray/master/v2ray",
    "https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/v2ray.txt",
    "https://raw.githubusercontent.com/Pawdroid/Free-servers/refs/heads/main/sub",
    "https://raw.githubusercontent.com/HakurouKen/free-node/main/public",
    "https://raw.githubusercontent.com/somemoo/v2rayfree/main/v2rayfree",
    "https://www.xrayvip.com/free.txt"  
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

# Function to parse base64 encoded content
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

# Function to parse plain text lines
def parse_plain_text(content: str) -> List[str]:
    return content.splitlines()

# Function to convert Clash proxy to V2Ray-style link
def clash_to_v2ray_link(proxy: Dict) -> str:
    try:
        proxy_type = proxy.get('type')
        if proxy_type == 'vmess':
            config = {
                'v': '2',
                'ps': proxy.get('name', proxy.get('server', '')),
                'add': proxy.get('server'),
                'port': proxy.get('port'),
                'id': proxy.get('uuid'),
                'aid': proxy.get('alterId', 0),
                'net': proxy.get('network', 'tcp'),
                'type': proxy.get('type', 'none'),
                'host': proxy.get('servername', ''),
                'path': proxy.get('path', ''),
                'tls': 'tls' if proxy.get('tls') else ''
            }
            encoded = base64.b64encode(json.dumps(config).encode('utf-8')).decode('utf-8')
            return f"vmess://{encoded}"
        elif proxy_type == 'ss':
            auth = f"{proxy.get('cipher')}:{proxy.get('password')}"
            encoded_auth = base64.b64encode(auth.encode('utf-8')).decode('utf-8')
            server_port = f"{proxy.get('server')}:{proxy.get('port')}"
            return f"ss://{encoded_auth}@{server_port}#{proxy.get('name', proxy.get('server'))}"
        elif proxy_type == 'trojan':
            server_port = f"{proxy.get('server')}:{proxy.get('port')}"
            sni = proxy.get('sni', '')
            query = f"?sni={sni}" if sni else ""
            return f"trojan://{proxy.get('password')}@{server_port}#{proxy.get('name', proxy.get('server'))}{query}"
        return ""
    except:
        return ""

# Function to extract node info based on format
def extract_nodes(url: str, content: str) -> List[Dict]:
    nodes = []
    format_type = "unknown"
    
    if url.endswith('.yaml') or 'clash' in url.lower():
        format_type = "yaml"
        proxies = parse_yaml_content(content)
        for proxy in proxies:
            link = clash_to_v2ray_link(proxy)
            if link:
                node = {
                    'type': proxy.get('type', 'unknown'),
                    'server': proxy.get('server'),
                    'port': proxy.get('port'),
                    'full_config': link
                }
                nodes.append(node)
    
    elif 'base64' in content.lower() or len(content) % 4 == 0:
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
            encoded = link.split('://')[1]
            decoded = base64.b64decode(encoded + '==').decode('utf-8')
            config = json.loads(decoded)
            return {
                'type': 'vmess',
                'server': config.get('add'),
                'port': config.get('port'),
                'full_config': link
            }
        elif scheme == 'ss':
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

# Function to test connectivity (port check or HTTP request test)
def test_connectivity(node: Dict) -> bool:
    if not node.get('server') or not node.get('port'):
        return False
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((node['server'], int(node['port'])))
        sock.close()
        print(f"Port test for {node['server']}:{node['port']} - {'Success' if result == 0 else 'Failed'}")
        return result == 0
    except Exception as e:
        print(f"Port test failed for {node['server']}:{node['port']}: {e}")
        return False

# Function to generate text file with working node links
def generate_node_file(working_nodes: List[Dict]) -> None:
    os.makedirs('test', exist_ok=True)
    with open('test/working_nodes.txt', 'w') as f:
        for node in working_nodes:
            f.write(f"{node['full_config']}\n")

# Main function with added total count and processed count
def main():
    all_nodes = []
    total_urls = len(URLS)
    processed_urls = 0
    
    for url in URLS:
        print(f"Processing URL {processed_urls + 1}/{total_urls}")
        content = download_content(url)
        processed_urls += 1
        
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
    
    # Generate text file with working node links
    generate_node_file(working_nodes)

if __name__ == "__main__":
    main()
