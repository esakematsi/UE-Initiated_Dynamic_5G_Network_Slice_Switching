#Requirements: 1 PDU Active Session at the time, Already registered to the network and one PDU Session is active,
#Only 2 CID profiles per PDU Session, Have the PDU Profiles already configured in the modem


import subprocess
import time
import re
import sys
import ipaddress
import argparse
import requests
import threading
import os


THRESHOLD_DEFAULT = 20.0
API_URL = "http://localhost:5000"
LOG_FILE = "iperf_output.log"
RE_THROUGHPUT = re.compile(r"(\d+(?:\.\d+)?)\s+(?:M|K)?bits/sec")
MAX_BELOW = 3
global below_threshold_count


def validate_ip(value):
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid IP address: {value}")


def validate_port(value):
    try:
        port = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Port must be an integer")
    if not (1 <= port <= 65535):
        raise argparse.ArgumentTypeError("Port must be between 1 and 65535")
    return port


def validate_threshold(value):
    try:
        t = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Threshold must be a number.")
    if t <= 0:
        raise argparse.ArgumentTypeError("Threshold must be a positive number.")
    return t


def parse_args():
    parser = argparse.ArgumentParser(description="iperf3 Goodput Monitor with Slice Switching")
    parser.add_argument("--server", type=validate_ip, required=True, help="iperf3 server IP")
    parser.add_argument("--port", type=validate_port, default=5201, help="iperf3 server port (default: 5201)")
    parser.add_argument("--threshold", type=validate_threshold, default=THRESHOLD_DEFAULT, help="Goodput threshold in Mbps (default: 2.0)")
    parser.add_argument("--debug", action="store_true", default=False, help="Enable debug output")
    return parser.parse_args()


def debug_print(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)



def fetch_network_status():
    try:
        status_resp = requests.get(f"{API_URL}/status", timeout=5)
        if status_resp.status_code != 200:
            print(f"Failed to fetch status: {status_resp.json()}")
            return None, None
        status = status_resp.json()

        alt_resp = requests.get(f"{API_URL}/alternative_slice", timeout=5)
        if alt_resp.status_code != 200:
            print(f"Failed to fetch alternative slice: {alt_resp.json()}")
            return None, None
        data = alt_resp.json()
        active_cid = data.get("Active_CID")
        al_profile = data.get("Alternative_CID", {})

        print("Network Status\n"
              f"Connected to DNN  : {status.get('Connected to DNN')}\n"
              f"Current Slice     : {status.get('Current Slice')}\n"
              f"Active CID        : {active_cid}\n"
              f"Alternative CID   : {al_profile.get('CID')}\n"
              f"Alternative Slice : {al_profile.get('Slice')}\n")
        return active_cid, al_profile

    except requests.RequestException as e:
        print(f"API request error: {e}")
        return None, None


def trigger_slice_switch(al_profile):
    al_cid = al_profile.get("CID")
    print(f"Goodput below threshold. Triggering slice switch to CID {al_cid}.")
    try:
        resp = requests.post(
            f"{API_URL}/activate_pdu",
            json={"CID": int(al_cid)},
            timeout=30,
        )
        if resp.status_code == 200:
            print(resp.json().get("Message"))
            return True
        else:
            print(f"Slice switch failed: {resp.json().get('Error')}")
            return False
    except requests.RequestException as e:
        print(f"API request error: {e}")
        return False





def clear_log():
    open(LOG_FILE, "w").close()




def launch_iperf(server, port):
    
    cmd= ["iperf3", "-c", server, "-p", str(port), "-t", "100","-R", "--logfile", LOG_FILE]
    try:
    #     log= open(LOG_FILE, "w")
        iperf_process= subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
        if iperf_process.poll() is not None:
            with open(LOG_FILE, "r") as f:
                print(f.read().strip())
            return None
        print(f"iperf3 started (PID {iperf_process.pid})")
        return iperf_process
    except Exception as e:
        print(f"Error launching iperf3: {e}")
        return None, None





def stop_iperf(iperf_process, log_file):
    if iperf_process and iperf_process.poll() is None:
        iperf_process.terminate()
        iperf_process.wait()
        print("iperf3 stopped.")

    # if log_file:
    #     log_file.close()
    






def monitor_log(threshold, switch_event, pause_event):
    global below_threshold_count 
    last_position= 0
    # last_switch_time= 0
    # COOLDOWN=30

    while True:
        try:
            with open(LOG_FILE, "r") as f:
                f.seek(last_position)
                lines= f.readlines()
                last_position= f.tell()

                for line in lines:
                    line= line.strip()
                    if not line:
                        continue
                    if "sender" in line or "receiver" in line:
                        continue

                    debug_print(line)

                    match= RE_THROUGHPUT.search(line)
                    if not match:
                        continue

                    throughput= float(match.group(1))
                    print(f"iperf3 throughput: {throughput:.2f} Mbps")

                    if pause_event.is_set():
                        continue

                    if throughput < threshold:
                        below_threshold_count += 1
                        print(f"Below threshold ({below_threshold_count}/{MAX_BELOW})")
                        if below_threshold_count >= MAX_BELOW:
                            # if time.monotonic() - last_switch_time >= COOLDOWN:
                            switch_event.set()
                            pause_event.set()
                            # last_switch_time = time.monotonic()
                            below_threshold_count = 0
                    else:
                        below_threshold_count = 0

        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Error reading log: {e}")

        # time.sleep(0.5)





def main():
    global DEBUG, below_threshold_count
    below_threshold_count= 0 

    args= parse_args()
    SERVER= args.server
    PORT= args.port
    THRESHOLD= args.threshold
    DEBUG= args.debug

    print(f"Starting iperf3 monitoring Server: {SERVER}, Port: {PORT}, Threshold: {THRESHOLD} Mbps")

    active_cid, al_profile = fetch_network_status()
    if not active_cid or not al_profile:
        print("Could not fetch network status. Exiting.")
        sys.exit(1)

    clear_log()
    iperf_proc= launch_iperf(SERVER, PORT)

    if not iperf_proc:
        print("Failed to launch iperf3. Exiting.")
        sys.exit(1)


    switch_event = threading.Event()
    pause_event = threading.Event()
    monitor_thread = threading.Thread(target=monitor_log, args=(THRESHOLD, switch_event, pause_event), daemon=True)
    monitor_thread.start()

    try:
        while True:
            if switch_event.is_set():
                switch_event.clear()

                success= trigger_slice_switch(al_profile)

                if success:
                    active_cid, al_profile = fetch_network_status()
                    if not al_profile:
                        print("Could not fetch network status after switch. Exiting.")
                        break
                below_threshold_count = 0
                pause_event.clear()

    except KeyboardInterrupt:
        print("\nKeyboard interrupt received. Stopping.")
        # stop_iperf(iperf_process, LOG_FILE )

    finally:
        stop_iperf(iperf_proc, LOG_FILE )
        print("iperf3 monitor stopped.")








if __name__ == "__main__":
    main()
