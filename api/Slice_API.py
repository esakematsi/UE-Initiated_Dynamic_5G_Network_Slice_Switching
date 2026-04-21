# API for Slice Selection Mechanism. Activate/ Deactivate Slice-Specific PDU Sessions on demand. One active PDU Session at a time. 

# Requirements: 1) quectel-CM data call, Quectel modem and qmi_wwan driver 2) quectel-CM accessible from any path, 
# 3) PDU CID Profiles already configured with AT+CGDCONT 


import time
import serial
import subprocess
import re
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import asyncio


SERIAL_PORT = "/dev/ttyUSB2"
BAUD_RATE = 115200
TIMEOUT = 1

p_num= None
switch_lock = asyncio.Lock()


def send_AT_command(command, ser,TIMEOUT=1):
    try:
        ser.write((command + "\r\n").encode())
        time.sleep(TIMEOUT)
        response = ser.read(ser.in_waiting or 1000).decode()
#        if response:
 #           print(response.strip())
        return response
    except serial.SerialException as e:
        print(f"Serial error: {e}")
        return None




def get_current_network_status(ser):

    #Get the CID of the active PDU session

    response = send_AT_command("AT+CGACT?", ser)
    active_cid = None
    try:
        for line in response.splitlines():
            if "+CGACT:" in line:
                parts = line.split(":")[1].strip().split(",")
                if len(parts) == 2 and parts[1].strip() == "1":
                    active_cid = parts[0].strip()
                    break
        else:
            print("No active PDU session found.")

    except Exception as e:
        print(f"Error parsing active PDU Session: {e}")
        return None, None




    #Get DNN, Current Slice, All available Slices

    response = send_AT_command("AT+CGDCONT?", ser)
    current_dnn = None
    current_slice = None
    profiles=[]
    p_num=0


    try:
        for line in response.splitlines():
            line=line.strip()

            if "+CGDCONT:" in line:
                parts = line.split(",")
                p_num+=1

                if len(parts) >= 21:
                    cid = parts[0].split(":")[1].strip()


                    dnn_full = parts[2].strip().strip('"')
                    dnn= dnn_full.split("_")[0]


                    slice_info = parts[16].strip().strip('"') #in HEX
                    if not slice_info or slice_info == "00":
                        slice_info = "Default Slice by Operator"

                    profiles.append({
                        "CID": cid,
                        "DNN": dnn,
                        "Slice": slice_info
                    })
                    if cid == active_cid:
                        current_slice = slice_info
                        current_dnn = dnn

        return {"Active_CID":active_cid, "Current_DNN": current_dnn, "Current_Slice": current_slice, "Available_Profiles": profiles}, p_num
        
    
    except Exception as e:
        print(f"Error parsing DNN and Slice: {e}")
        return None, None 






#This returns the first CID profile with the same DNN and a different Slice, Useful for switching between 2 available Slices
def get_alternative_cid(info):
    active_cid  = info["Active_CID"]
    current_dnn = info["Current_DNN"]



    for profile in info["Available_Profiles"]:
            if profile["DNN"] == current_dnn and profile["CID"] != active_cid:
                return profile
    
    return None





def monitor_quectel_output(process):

    
    lease_found=False
    start_time= time.time()
    timeout= 5

    while True:

        if time.time() - start_time > timeout and not lease_found:
                # print("Could not establish PDU Session with this CID. Try again.")
                # disconnect_sessions()
                break

        line = process.stdout.readline()
        line= line.strip()
                
        if not line:
            continue

        print(line)
                
        if re.search(r"udhcpc: lease of\s+\d+\.\d+\.\d+\.\d+\s+obtained", line):
            lease_found= True
            print("\nPDU Session successfully established.")
            break

            # break

        
    if not lease_found:
        # disconnect_sessions()
        print("Could not establish PDU Session with this CID. Try again.")
        return False
    
    return True
    




def activate_slice(requested_slice):

    
    print(f"Attempting to switch to CID {requested_slice}...\n")
    
    
    try:
        cid_target = str(int(requested_slice))
        cmd = ["sudo", "quectel-CM", "-n", cid_target]


        # disconnect_sessions()        
        
        
        process= subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text= True, bufsize=1)
                
        return monitor_quectel_output(process)

        	
    except Exception as e:
        print(f"Error switching slice: {e}")





def validate_cid_input(requested_cid, p_num):
    if not str(requested_cid).isdigit():
        print ("Error: CID must be a numeric value")
        return False 
    	
    cid_num= int(requested_cid)
    if cid_num in [0,1,2,3]:
        print(f"Can not access this PDU Profile:", {cid_num})
        return False
    	
    if cid_num > p_num:
        print("Error. PDU Profile out of range")
        return False
    	
    return True
    
    



def init_serial():
    try:
        return serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT)
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        return None





def disconnect_sessions():
    try:
        subprocess.call(["sudo","pkill","-INT","-f","quectel-CM",])
        time.sleep(1)
        result = subprocess.run(["pgrep", "-f", "quectel-CM"], capture_output=True)
        if result.returncode == 0:
            print("[disconnect] quectel-CM still running, force killing ...")
            subprocess.call(["sudo", "pkill", "-KILL", "-f", "quectel-CM"])
            time.sleep(1)

        print("PDU Session released.")
        return True
    except Exception as e:
        print(f"Failed to release the PDU Session: {e}")
        return False



# API Endpoints 


app = FastAPI()

class SliceRequest(BaseModel):
    CID: int





############### CORS ###############

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]

)

####################################### 





@app.get('/status')
def get_status():
    global p_num
    ser = init_serial()
    if not ser:
        return JSONResponse(status_code=500, content={"Error": "Failed to open serial port"})

    info, p_num = get_current_network_status(ser)
    ser.close()

    if not info:
        return JSONResponse(status_code=500, content={"Error": "Failed to retrieve network status"})


    return {
        "Connected to DNN": info["Current_DNN"],
        "Current Slice": info["Current_Slice"],
        # "Number of Profiles": p_num,
        # "Other Available Slices": info["Available_Profiles"]
    }




@app.get('/available_slices')
def get_slices():
    global p_num
    ser = init_serial()
    if not ser:
        return JSONResponse(status_code=500, content={"Error": "Failed to open serial port"})
        

    info, p_num= get_current_network_status(ser)
    ser.close()

    if not info:
        return JSONResponse(status_code=500, content={"Error": "Failed to retrieve network status"})

    return {
        # "Connected to DNN": info["Current_DNN"],
        # "Current Slice": info["Current_Slice"],
        "Number of Profiles": p_num,
        "Available Slices": info["Available_Profiles"]
    }




@app.get('/alternative_slice')
def get_alternative_cid_profile():
    ser = init_serial()
    if not ser:
        return JSONResponse(status_code=500, content={"Error": "Failed to open serial port"})
 
    info, _ = get_current_network_status(ser)
    ser.close()
 
    if not info:
        return JSONResponse(status_code=500, content={"Error": "Failed to retrieve network status"})

    al_cid = get_alternative_cid(info)
    if al_cid is None:
        return JSONResponse(status_code=404, content={"Error": "No alternative CID found with the same DNN."})

 
    return {
        "Active_CID":     info["Active_CID"],
        "Alternative_CID":  al_cid
    }
 



@app.post('/activate_pdu')
async def activate_pdu_session(request: SliceRequest):
    if switch_lock.locked():      
        return JSONResponse(status_code=429, content={"Error": "A slice switch is already in progress. Try again later."})

    async with switch_lock:
        requested_cid= request.CID

        global p_num
        if not p_num:
            ser = init_serial()
            if not ser:
                return JSONResponse(status_code=500, content={"Error": "Failed to open serial port"})

            info, p_num = get_current_network_status(ser)
            ser.close()
            if not info:
                return JSONResponse(status_code=500, content={"Error": "Failed to retrieve PDU profile info."})




        if not requested_cid:
            return JSONResponse(status_code=400, content={"Error": "CID not provided."})

            

        if not validate_cid_input(requested_cid,p_num):
            return JSONResponse(status_code=400, content={"Error": "Cannot access this Slice. Choose a different CID."})


            
        
        suc= activate_slice(requested_cid)
        if suc:
            return JSONResponse(status_code=200, content={"Message": f"PDU Session successfully established for CID {requested_cid}."})
        else:
            return JSONResponse(status_code=500, content={"Error": "Failed to establish PDU Session for the requested CID."})


        



@app.post('/disconnect')
def disconnect_all():
    if disconnect_sessions():
        return JSONResponse(status_code=200, content={"Message": "All PDU Sessions disconnected."})

    else:
        return JSONResponse(status_code=500, content={"Error": "Failed to disconnect PDU Sessions."})


        
