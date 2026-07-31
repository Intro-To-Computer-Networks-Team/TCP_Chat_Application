import socket
import time
import concurrent.futures
import statistics
from typing import List, Tuple

# ==========================================
# 1. Global Server Configuration
# ==========================================
HOST = '127.0.0.1'  # Server IP address (localhost)
PORT = 4000  # Must match the chat server's listening port
SOCKET_TIMEOUT = 5.0  # Maximum socket receive timeout in seconds


# ==========================================
# 2. Protocol Adapter
# ==========================================
def create_message_payload(username: str, msg_index: int) -> bytes:
    """
    Format: 'recipient:content'
    Addressing messages to ourselves ensures the server routes the payload
    back to our own socket, allowing accurate RTT latency measurement.
    """
    raw_message = f"{username}: Benchmark message {msg_index}"
    return raw_message.encode('utf-8')


# ==========================================
# 3. Client Simulation Worker
# ==========================================
def simulate_client(client_id: int, num_messages: int, delay_sec: float) -> Tuple[int, int, List[float]]:
    """
    Simulates an authenticated TCP client lifecycle:
    1. Connects and sends username during authentication handshake.
    2. Sends sequential round-trip messages and records latencies.
    """
    success_count = 0
    failure_count = 0
    latencies_ms = []

    username = f"BenchUser_{client_id}"

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(SOCKET_TIMEOUT)
            sock.connect((HOST, PORT))

            # --- Authentication Handshake ---
            sock.recv(1024)  # Welcome prompt
            sock.sendall(f"{username}\n".encode('utf-8'))  # Send username
            time.sleep(0.3)  # Allow server DB registration
            sock.recv(2048)  # Clear welcome & CONTACTS buffer

            # --- Messaging Loop ---
            for i in range(num_messages):
                payload = create_message_payload(username, i)
                start_time = time.perf_counter()

                try:
                    sock.sendall(payload)
                    response = sock.recv(1024)
                    end_time = time.perf_counter()

                    if response and username.encode('utf-8') in response:
                        latencies_ms.append((end_time - start_time) * 1000)
                        success_count += 1
                    else:
                        failure_count += 1

                except (socket.timeout, socket.error):
                    failure_count += 1

                if delay_sec > 0:
                    time.sleep(delay_sec)

    except Exception as e:
        print(f"[!] {username} connection failed: {e}")
        failure_count += num_messages

    return success_count, failure_count, latencies_ms


# ==========================================
# 4. Suite Executor & Reporting
# ==========================================
def run_test_scenario(test_name: str, num_clients: int, messages_per_client: int, delay_sec: float):
    """
    Runs a specific benchmark scenario and prints a detailed metric report.
    """
    total_expected = num_clients * messages_per_client
    print("\n" + "=" * 55)
    print(f" [TEST] {test_name}")
    print("=" * 55)
    print(f" [*] Clients: {num_clients} | Msgs/Client: {messages_per_client} | Inter-msg Delay: {delay_sec}s")
    print(f" [*] Target Expected Messages: {total_expected}")

    start_benchmark = time.perf_counter()
    total_success = 0
    total_failure = 0
    all_latencies = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_clients) as executor:
        futures = [
            executor.submit(simulate_client, client_id, messages_per_client, delay_sec)
            for client_id in range(num_clients)
        ]

        for future in concurrent.futures.as_completed(futures):
            success, failure, latencies = future.result()
            total_success += success
            total_failure += failure
            all_latencies.extend(latencies)

    duration = time.perf_counter() - start_benchmark

    # --- Print Scenario Results ---
    print("-" * 55)
    print(f" Elapsed Time:           {duration:.2f} seconds")
    print(f" Successful Messages:    {total_success} / {total_expected}")
    print(f" Failed Messages:        {total_failure}")

    if duration > 0 and total_success > 0:
        print(f" Throughput (MPS):       {total_success / duration:.2f} msg/sec")

    if all_latencies:
        avg_lat = statistics.mean(all_latencies)
        p95_lat = statistics.quantiles(all_latencies, n=20)[18] if len(all_latencies) >= 20 else max(all_latencies)
        print(f" Average Latency:        {avg_lat:.2f} ms")
        print(f" 95th Percentile (P95):  {p95_lat:.2f} ms")
        print(f" Max Latency:            {max(all_latencies):.2f} ms")
    print("=" * 55)

    # Brief pause between test scenarios to allow server socket cleanup
    time.sleep(1.0)


# ==========================================
# 5. Main Benchmark Suite Execution
# ==========================================
def main():
    print("#######################################################")
    print("     TCP CHAT SERVER - PERFORMANCE BENCHMARK SUITE     ")
    print("#######################################################")

    # Test 1: Baseline routing & database latency (no lock contention)
    run_test_scenario(
        test_name="Baseline Latency Test (Single Client)",
        num_clients=1,
        messages_per_client=30,
        delay_sec=0.02
    )

    # Test 2: Standard throughput at 100% server capacity
    run_test_scenario(
        test_name="Full Capacity Load Test (5 Concurrent Clients)",
        num_clients=5,
        messages_per_client=20,
        delay_sec=0.02
    )

    # Test 3: Mutex lock contention & burst handling (zero sleep)
    run_test_scenario(
        test_name="Rapid-Fire Burst Stress Test (Zero Delay)",
        num_clients=5,
        messages_per_client=20,
        delay_sec=0.0
    )


if __name__ == '__main__':
    main()