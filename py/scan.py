import http.client
import concurrent.futures
import os
import sys

# 配置
INPUT_FILE = "py/bj_list.txt"
OUTPUT_FILE = "test/beijing_hotel.m3u"
SCAN_RANGES = list(range(1, 21)) + list(range(1000, 1100))

def check_link(ip_port, cid):
    path = f"/tsfile/live/{cid}_1.m3u8"
    try:
        host, port = ip_port.strip().split(':')
        conn = http.client.HTTPConnection(host, int(port), timeout=2)
        conn.request("GET", path)
        res = conn.getresponse()
        status = res.status
        conn.close()
        if status == 200:
            # 实时打印发现的频道，flush=True 确保立即显示在 GitHub 日志中
            print(f"  [√] 发现有效: {ip_port} -> ID {cid}", flush=True)
            return f"#EXTINF:-1,北京酒店-{cid}\nhttp://{ip_port}{path}"
    except:
        pass
    return None

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"错误: 找不到 {INPUT_FILE}", flush=True)
        return

    with open(INPUT_FILE, 'r') as f:
        ips = [line.strip() for line in f if line.strip()]

    print(f"--- 开始扫描 {len(ips)} 个北京服务器目标 ---", flush=True)
    results = ["#EXTM3U"]
    
    # 为了看到过程，我们按 IP 顺序扫描，但在 IP 内部进行并发 ID 扫描
    for count, ip in enumerate(ips, 1):
        print(f"[{count}/{len(ips)}] 正在扫描服务器: {ip} ...", flush=True)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(check_link, ip, cid) for cid in SCAN_RANGES]
            found_count = 0
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                if res:
                    results.append(res)
                    found_count += 1
        
        if found_count > 0:
            print(f"      完成！该服务器扫描到 {found_count} 个频道。", flush=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(results))
    
    print(f"\n--- 扫描结束，共汇总 {len(results)-1} 个有效频道 ---", flush=True)

if __name__ == "__main__":
    main()
