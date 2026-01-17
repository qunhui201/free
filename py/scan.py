import requests
import re
import concurrent.futures
import os
import base64

# --- 配置区 ---
# 搜索关键词：建议扩大搜索范围，去掉 js 限制，只搜路径
KEYWORD = '"tsfile/live" && region="Hunan"'
QUERY_B64 = base64.b64encode(KEYWORD.encode()).decode()

OUTPUT_M3U = "test/hunan_hotel.m3u"
ALIVE_SERVER_FILE = "test/alive_servers.txt"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
}

def get_ips_from_fofa():
    """提取 FOFA 网页 IP"""
    all_ips = set()
    for page in range(1, 4):
        url = f"https://fofa.info/result?qbase64={QUERY_B64}&page={page}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            # 改进正则，防止抓到重复或错误的 IP
            ips = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+', r.text)
            all_ips.update(ips)
        except: pass
    return list(all_ips)

def check_single_channel(ip_port, cid, name=None):
    """通用频道检测"""
    url = f"http://{ip_port}/tsfile/live/{cid}_1.m3u8"
    try:
        r = requests.head(url, timeout=2)
        if r.status_code == 200:
            channel_name = name if name else f"频道-{cid}"
            return f"#EXTINF:-1,{channel_name}\n{url}"
    except: pass
    return None

def process_server(ip_port):
    """处理单个服务器：先试字典，不行就爆破"""
    print(f"正在测试服务器: {ip_port}", flush=True)
    results = []
    
    # 尝试下载字典
    js_url = f"http://{ip_port}/iptv/live/zh_cn.js"
    try:
        r = requests.get(js_url, timeout=3)
        if r.status_code == 200:
            ids = re.findall(r'"channelId":"(\d+)"', r.text)
            names = re.findall(r'"channelName":"([^"]+)"', r.text)
            dic = dict(zip(ids, names))
            if dic:
                print(f"  [√] 发现字典: {ip_port}，开始按需检测...", flush=True)
                for cid, name in dic.items():
                    res = check_single_channel(ip_port, cid, name)
                    if res: results.append(res)
                return results, True # 返回结果和“是否为真源”标志
    except: pass

    # 如果没有字典，执行强制爆破模式 (针对 1-20 和 1000-1050)
    print(f"  [!] 无字典，进入爆破模式: {ip_port}", flush=True)
    scan_list = list(range(1, 21)) + list(range(1000, 1051))
    for cid in scan_list:
        res = check_single_channel(ip_port, cid)
        if res: results.append(res)
    
    return results, len(results) > 0

def main():
    os.makedirs("test", exist_ok=True)
    ips = get_ips_from_fofa()
    print(f"--- 提取到 {len(ips)} 个潜在 IP ---", flush=True)

    final_m3u = ["#EXTM3U"]
    real_ips = []

    # 使用并发处理每个服务器
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_ip = {executor.submit(process_server, ip): ip for ip in ips}
        for future in concurrent.futures.as_completed(future_to_ip):
            ip = future_to_ip[future]
            server_results, is_alive = future.result()
            if is_alive:
                final_m3u.extend(server_results)
                real_ips.append(ip)

    # 保存
    with open(ALIVE_SERVER_FILE, 'w') as f:
        f.write("\n".join(real_ips))
    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("\n".join(final_m3u))

    print(f"\n任务结束！发现 {len(real_ips)} 个真源，共汇总 {len(final_m3u)-1} 个频道。", flush=True)

if __name__ == "__main__":
    main()
