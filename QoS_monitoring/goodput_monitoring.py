# It captures the total bytes received on a specific TCP connection (server and port filter) every 1 sec and calculates 
# the goodput in Mbps.  

# The script uses ss tool to communicate with the Linux kernel for socket info, extracts the total_bytes parameter every sec, calculates the differnce in total bytes and time from the previous measurement and calculates the
# goodput. The results are sent to a queue. 

# Stops automatically when there is no TCP Socket (No active TCP Connection).  

# At startup, the alternate CID is fetched from the Slice Selection API.
# When goodput falls below a specific threshold for 3 measurements, the
# slice switch is triggered via POST /activate_pdu.

# PARAMETERS : SOURCE IP, PORT, THRESHOLD, DEBUG MODE



import subprocess
import time
import re
from datetime import datetime, timezone
import argparse 
import sys
import ipaddress
import os
import requests




SEC = 1
RE_BYTES_RECEIVED = re.compile(r"\bbytes_received:(\d+)\b")
THRESHOLD_DEFAULT = 2 # Mbps
API_URL = "http://localhost:5000"



global prev_total_bytes, prev_time
prev_total_bytes=None
prev_time=None






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



def validate_threshold(threshold):
    try:
        t = float(threshold)
    except ValueError:
        raise argparse.ArgumentTypeError("Threshold must be a number.")
    if t <= 0:
        raise argparse.ArgumentTypeError("Threshold must be a positive number.")
    return t




def debug_print(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)





def parse_args():
    try:
       
        parser = argparse.ArgumentParser(description="Goodput Measurement Script")

        parser.add_argument("--source-ip", type=validate_ip, required= True, help="Source IP to filter (default from default_config.yaml)")
        parser.add_argument("--port", type=validate_port, required=True, help="Source port to filter (default from default_config.yaml)")
        parser.add_argument("--threshold", type=validate_threshold, default=THRESHOLD_DEFAULT, help="Goodput threshold in Mbps (default: 2.0)")
        parser.add_argument("--debug", action="store_true", default=False, help="Enable debug output")
        

        return parser.parse_args()

    except Exception as e:
        print(f"Error parsing arguments: {e}")
        sys.exit(1)





def run_ss():

    cmd = ["ss", "-niH", f"dst", SRC_IP, "and", "dport", "=", f":{PORT}"]

    try:
        proc= subprocess.run(cmd, text=True, capture_output=True, timeout=SEC)


        if proc.returncode != 0:
            print(f"ss command failed with return code {proc.returncode}")
            return None
    

        return proc

    except subprocess.TimeoutExpired:
        debug_print("ss command timed out")
        return None

    except Exception as e:
        print(f"Error occured: {e}")
        return None






def extract_total_bytes(ss_output):

   
    bytes_received = 0

    try:

        for line in ss_output.splitlines():
            bytes_match = RE_BYTES_RECEIVED.search(line)
    

            if bytes_match:
                bytes_received += int(bytes_match.group(1))


        return bytes_received


    except Exception as e:
        print(f"Error occured while extracting retransmissions: {e}")
        return None




def goodput_per_sec(total_bytes, cur_time):
    
    global prev_total_bytes 
    global prev_time

    try: 

        if (prev_total_bytes is None or prev_time is None):
            prev_total_bytes = total_bytes
            prev_time = cur_time
            # goodput=total_bytes/prev_time
            # goodput_mbps= (goodput*8)/1_000_000
            print(f"First measurement, initializing values.")
            return True, 0.0
        
        if total_bytes == 0:
            prev_total_bytes = None
            prev_time = None
            debug_print("No active TCP connections found.")
            return False, None




        if total_bytes<prev_total_bytes:
            debug_print("Total bytes decreased, possible TCP reset. Reinitializing values.")
            prev_total_bytes = total_bytes
            prev_time = cur_time
            return True, 0.0



        d_bytes= total_bytes - prev_total_bytes
        d_time= cur_time - prev_time


        if d_time <=0:
            debug_print("Non-positive time difference detected, skipping goodput calculation.")
            prev_total_bytes = total_bytes
            prev_time = cur_time
            return True, 0.0


        goodput= d_bytes / d_time

        goodput_mbps= (goodput*8.0)/(1024*1024)

        

        goodput_MBps = goodput / (1024*1024)
        debug_print(f"Goodput: {goodput_mbps:.2f} Mbps")

        # print(f"Goodput: {goodput:.3f} MBps")


        prev_total_bytes = total_bytes
        prev_time = cur_time

        return True, goodput_mbps

    
    except Exception as e:
        print(f"Error occured while calculating retransmissions per sec: {e}")
        return False, None




def fetch_network_status():
    try:
        status_resp = requests.get(f"{API_URL}/status", timeout=5)
        if status_resp.status_code != 200:
            print(f"Failed to fetch status: {status_resp.json()}")
            return None, None
        status = status_resp.json()
        # print(status)

        alt_resp = requests.get(f"{API_URL}/alternative_slice", timeout=5)
        if alt_resp.status_code != 200:
            print(f"Failed to fetch alternative slice: {alt_resp.json()}")
            return None, None
        data = alt_resp.json()
        active_cid = data.get("Active_CID")
        al_profile = data.get("Alternative_CID", {})

        print("Network Status\n" 
            f"Connected to DNN: {status.get('Connected to DNN')}\n"
            f"Current Slice   : {status.get('Current Slice')}\n"
            f"Active CID      : {active_cid}\n"
            f"Alternative CID : {al_profile.get('CID')}\n"
            f"Alternative Slice : {al_profile.get('Slice')}\n"
            )
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
            print(f"{resp.json().get('Message')}")
            return True
        else:
            print(f"Slice switch failed: {resp.json().get('Error')}")
            return False
    except requests.RequestException as e:
        print(f"API request error: {e}")
        return False


def main():

    global SRC_IP, PORT, THRESHOLD, DEBUG

    args = parse_args()

    SRC_IP = args.source_ip
    PORT = args.port
    DEBUG = args.debug
    THRESHOLD = args.threshold

    print(f"Starting goodput monitoring: IP {SRC_IP}, Port {PORT} with Threshold {THRESHOLD} Mbps")

    active_cid, al_profile = fetch_network_status()
    if not active_cid or not al_profile:
        print("Could not fetch network status. Exiting.")
        sys.exit(1)

    below_threshold_count = 0
    MAX_BELOW = 3

    try:
        while True:
            ss_proc = run_ss()

            if ss_proc is None:
                time.sleep(SEC)
                continue

            total_bytes_received = extract_total_bytes(ss_proc.stdout)
            cur_time = time.monotonic()

            ok, goodput = goodput_per_sec(total_bytes_received, cur_time)

            if not ok:
                print("Socket is closed, no active connections.")
                break

            if goodput == 0.0:
                time.sleep(SEC)
                continue

            print(f"Goodput: {goodput:.2f} Mbps")

            if goodput < THRESHOLD:
                below_threshold_count += 1
                print(f"Below threshold ({below_threshold_count}/{MAX_BELOW})")

                if below_threshold_count >= MAX_BELOW:
                    success = trigger_slice_switch(al_profile)
                    below_threshold_count = 0

                    if success:
                        active_cid, al_profile = fetch_network_status()
                        if not al_profile:
                            print("Could not fetch network status after switch. Exiting.")
                            break
            else:
                below_threshold_count = 0

            time.sleep(SEC)

    except KeyboardInterrupt:
        print("\nKeyboard interrupt received. Stopping capture.")

    finally:
        print("Goodput measurement stopped.")




if __name__ == "__main__":
    main()




