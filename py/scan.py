import http.client
import concurrent.futures
import os

# 配置
INPUT_FILE = "py/bj_list.txt"
ALIVE_SERVER_FILE = "test/alive_servers.txt"  # 保存活着的服务器，下次直接用
OUTPUT_M3U = "test/beijing_hotel.m3u"
TEST_PATH = "/tsfile/live/1001_1.m3u8"  # 用 CCTV-1 做真伪校验
SCAN_RANGES = list(range(1, 21)) + list(range(1000, 1100))

def check_server_real(ip_port):
    """第一步 & 第二步：不仅要活着，还得有直播流特征"""
    try:
        host, port = ip_port.strip().split(':')
        conn = http.client.HTTPConnection(host, int(port), timeout=3)
        # 尝试请求 CCTV-1 路径
        conn.request("GET", TEST_PATH)
        res = conn.getresponse()
        status = res.status
        conn.close()
        if status == 200:
            print(f"  [发现真源] {ip_port} 验证通过，准许深挖。", flush=True)
            return ip_port
    except:
        pass
    return None

def scan_ids(ip_port, cid):
    """第三步：对验证通过的源进行 ID 扫描"""
    path = f"/tsfile/live/{cid}_1.m3u8"
    try:
        host, port = ip_port.split(':')
        conn = http.client.HTTPConnection(host, int(port), timeout=2)
        conn.request("GET", path)
        res = conn.getresponse()
        if res.status == 200:
            return f"#EXTINF:-1,北京酒店-{cid}\nhttp://{ip_port}{path}"
        conn.close()
    except:
        pass
    return None

def main():
    os.makedirs("test", exist_ok=True)
    if not os.path.exists(INPUT_FILE):
        print(f"错误: 找不到输入文件 {INPUT_FILE}")
        return

    with open(INPUT_FILE, 'r') as f:
        raw_ips = list(set([line.strip() for line in f if ":" in line]))

    print(f"--- 阶段 1 & 2: 正在从 {len(raw_ips)} 个目标中筛选真实源 ---", flush=True)
    real_servers = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        results = list(executor.map(check_server_real, raw_ips))
        real_servers = [r for r in results if r]

    # 保存活着的服务器，留作种子
    with open(ALIVE_SERVER_FILE, 'w') as f:
        f.write("\n".join(real_servers))
    
    if not real_servers:
        print("!!! 警告：本次抓取的 IP 中没有一个包含有效直播流路径。")
        return

    print(f"--- 阶段 3: 发现 {len(real_servers)} 个真实源，开始深挖频道 ---", flush=True)
    m3u_results = ["#EXTM3U"]
    
    for ip in real_servers:
        print(f"正在扫描有效服务器: {ip}", flush=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(scan_ids, ip, cid) for cid in SCAN_RANGES]
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                if res: m3u_results.append(res)

    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_results))

    print(f"\n扫描结束！共汇总 {len(m3u_results)-1} 个有效频道。")
    print(f"有效服务器列表已更新至: {ALIVE_SERVER_FILE}")

if __name__ == "__main__":
    main()
