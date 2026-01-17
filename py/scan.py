import http.client
import concurrent.futures
import os

# 定义配置
INPUT_FILE = "bj_list.txt"
OUTPUT_FILE = "beijing_hotel.m3u"
# 北京联通/移动源常见的 ID 段
SCAN_RANGES = list(range(1, 51)) + list(range(1000, 1100))

def check_link(ip_port, cid):
    path = f"/tsfile/live/{cid}_1.m3u8"
    try:
        host, port = ip_port.strip().split(':')
        conn = http.client.HTTPConnection(host, int(port), timeout=1.5)
        conn.request("GET", path)
        res = conn.getresponse()
        status = res.status
        conn.close()
        if status == 200:
            return f"#EXTINF:-1,北京酒店-{cid}\nhttp://{ip_port}{path}"
    except:
        pass
    return None

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"找不到 {INPUT_FILE}，请先上传 IP 列表。")
        return

    with open(INPUT_FILE, 'r') as f:
        ips = [line.strip() for line in f if line.strip()]

    print(f"开始扫描 {len(ips)} 个北京服务器...")
    final_m3u = ["#EXTM3U"]
    
    # 针对每个 IP 开启线程扫描
    for ip in ips:
        print(f"正在扫描: {ip}")
        with concurrent.futures.ThreadPoolExecutor(max_workers=40) as executor:
            # 这里的扫描逻辑是：针对每一个 IP，并发扫它的 ID 段
            futures = [executor.submit(check_link, ip, cid) for cid in SCAN_RANGES]
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    final_m3u.append(result)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_m3u))
    
    print(f"生成完成！共找到 {len(final_m3u)-1} 个有效频道。")

if __name__ == "__main__":
    main()
