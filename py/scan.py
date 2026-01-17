import http.client
import concurrent.futures
import os

# 配置
INPUT_FILE = "py/bj_list.txt"
ALIVE_SERVER_FILE = "test/alive_servers.txt"
OUTPUT_M3U = "test/beijing_hotel.m3u"
TEST_PATH = "/tsfile/live/1001_1.m3u8"
SCAN_RANGES = list(range(1, 21)) + list(range(1000, 1100))

def check_server_real(ip_port):
    """仅负责探测服务器是否含有特征路径"""
    try:
        host, port = ip_port.strip().split(':')
        conn = http.client.HTTPConnection(host, int(port), timeout=3)
        conn.request("GET", TEST_PATH)
        res = conn.getresponse()
        status = res.status
        conn.close()
        if status == 200:
            return ip_port
    except:
        pass
    return None

def scan_ids(ip_port, cid):
    """仅负责对已知活源进行频道深挖"""
    path = f"/tsfile/live/{cid}_1.m3u8"
    try:
        host, port = ip_port.split(':')
        conn = http.client.HTTPConnection(host, int(port), timeout=2)
        conn.request("GET", path)
        if conn.getresponse().status == 200:
            return f"#EXTINF:-1,北京酒店-{cid}\nhttp://{ip_port}{path}"
        conn.close()
    except:
        pass
    return None

def main():
    os.makedirs("test", exist_ok=True)
    if not os.path.exists(INPUT_FILE):
        print(f"错误: 找不到 {INPUT_FILE}")
        return

    with open(INPUT_FILE, 'r') as f:
        raw_ips = list(set([line.strip() for line in f if ":" in line]))

    # --- 阶段 1：全量 IP 扫描（不测完不进入下一步） ---
    print(f">>> 阶段 1: 开始全量探测 {len(raw_ips)} 个 IP 的特征路径...", flush=True)
    real_servers = []
    
    # 使用更高并发快速过一遍所有 IP
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        # map 会保持顺序并等待所有任务完成
        results = list(executor.map(check_server_real, raw_ips))
        real_servers = [r for r in results if r]

    # 立即写入存活列表（此时第一步已彻底结束）
    with open(ALIVE_SERVER_FILE, 'w') as f:
        f.write("\n".join(real_servers))
    
    print(f">>> 阶段 1 结束。共从 {len(raw_ips)} 个目标中筛选出 {len(real_servers)} 个真实源。", flush=True)
    for s in real_servers:
        print(f"    [有效种子]: {s}", flush=True)

    if not real_servers:
        print("!!! 未发现任何真实源，流程终止。")
        return

    # --- 阶段 2：深挖阶段（仅针对筛选出的 real_servers） ---
    print(f"\n>>> 阶段 2: 开始对这 {len(real_servers)} 个真实源进行频道深挖...", flush=True)
    m3u_results = ["#EXTM3U"]
    
    for ip in real_servers:
        print(f"正在深度扫描服务器: {ip} ...", flush=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(scan_ids, ip, cid) for cid in SCAN_RANGES]
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                if res: m3u_results.append(res)

    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_results))

    print(f"\n>>> 扫描任务全部完成！")
    print(f"最终有效频道总数: {len(m3u_results)-1}")

if __name__ == "__main__":
    main()
