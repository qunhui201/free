import requests
import re
import concurrent.futures
import os

# --- 配置区 ---
# 1. 你在浏览器里搜索好的 FOFA URL (记得在网页上翻页，或者把每页显示数量调大)
SEARCH_URL = "https://fofa.info/result?qbase64=InRzZmlsZS9saXZlIiAmJiByZWdpb249IkJlaWppbmci"

ALIVE_SERVER_FILE = "test/alive_servers.txt"
OUTPUT_M3U = "test/beijing_hotel.m3u"

# 模拟浏览器 Header
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def get_ips_from_web(url):
    """直接从 FOFA 网页提取 IP"""
    print(f">>> 正在读取 FOFA 网页数据...")
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        # 匹配 IP:PORT 格式
        pattern = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+'
        ips = list(set(re.findall(pattern, r.text)))
        print(f"--- 网页提取到 {len(ips)} 个潜在 IP ---")
        return ips
    except Exception as e:
        print(f"提取失败: {e}")
        return []

def get_channel_info(ip_port):
    """自动获取该服务器的频道字典"""
    js_url = f"http://{ip_port}/iptv/live/zh_cn.js"
    try:
        r = requests.get(js_url, timeout=3)
        if r.status_code == 200:
            # 提取 ID 和 频道名
            ids = re.findall(r'"channelId":"(\d+)"', r.text)
            names = re.findall(r'"channelName":"([^"]+)"', r.text)
            return dict(zip(ids, names))
    except:
        pass
    return None

def check_link(ip_port, cid, name):
    """验证频道真实性"""
    url = f"http://{ip_port}/tsfile/live/{cid}_1.m3u8"
    try:
        # 只取头信息，不下载数据，极速验证
        r = requests.head(url, timeout=2)
        if r.status_code == 200:
            print(f"  [√] 成功: {name}")
            return f"#EXTINF:-1,{name}\n{url}"
    except:
        pass
    return None

def main():
    os.makedirs("test", exist_ok=True)
    
    # 1. 抓取
    raw_ips = get_ips_from_web(SEARCH_URL)
    if not raw_ips: return

    # 2. 识别字典 (阶段 1)
    print(">>> 阶段 1: 正在识别服务器频道字典...")
    valid_servers = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        future_to_ip = {executor.submit(get_channel_info, ip): ip for ip in raw_ips}
        for future in concurrent.futures.as_completed(future_to_ip):
            ip = future_to_ip[future]
            dic = future.result()
            if dic:
                valid_servers.append((ip, dic))

    # 3. 深度测活 (阶段 2)
    print(f">>> 阶段 2: 正在对 {len(valid_servers)} 个有效源进行深度验证...")
    final_m3u = ["#EXTM3U"]
    for ip, dic in valid_servers:
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(check_link, ip, cid, name) for cid, name in dic.items()]
            for f in concurrent.futures.as_completed(futures):
                res = f.result()
                if res: final_m3u.append(res)

    # 4. 保存
    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("\n".join(final_m3u))
    
    print(f"\n任务结束！共生成 {len(final_m3u)-1} 个有效频道。")

if __name__ == "__main__":
    main()
