#!/usr/bin/env python3
import os, subprocess, sys, time, threading

def read_output(pipe, prefix):
    for line in iter(pipe.readline, ''):
        print(f"[{prefix}] {line.strip()}")
    pipe.close()

def main():
    print("🚀 Starting services...")
    
    # 1. Start Streamlit
    env = os.environ.copy()
    env['STREAMLIT_SERVER_PORT'] = '8501'
    st_cmd = [sys.executable, "-m", "streamlit", "run", "dashboard.py", "--server.port", "8501", "--server.headless", "true"]
    st_proc = subprocess.Popen(st_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    
    t_st_out = threading.Thread(target=read_output, args=(st_proc.stdout, "Streamlit"))
    t_st_err = threading.Thread(target=read_output, args=(st_proc.stderr, "Streamlit_Err"))
    t_st_out.daemon = True
    t_st_err.daemon = True
    t_st_out.start()
    t_st_err.start()

    time.sleep(5)

    # 2. Start LocalTunnel
    # We assume 'lt' is in path (npm install -g localtunnel)
    lt_cmd = "lt --port 8501"
    lt_proc = subprocess.Popen(lt_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    t_lt_out = threading.Thread(target=read_output, args=(lt_proc.stdout, "LT"))
    t_lt_err = threading.Thread(target=read_output, args=(lt_proc.stderr, "LT_Err"))
    t_lt_out.daemon = True
    t_lt_err.daemon = True
    t_lt_out.start()
    t_lt_err.start()

    print("✅ Services started. Press Ctrl+C to stop.")
    
    try:
        while True:
            time.sleep(1)
            if st_proc.poll() is not None:
                print("❌ Streamlit exited!")
                break
            if lt_proc.poll() is not None:
                print("❌ LocalTunnel exited!")
                break
    except KeyboardInterrupt:
        print("\n🛑 Stopping...")
        st_proc.terminate()
        lt_proc.terminate()

if __name__ == "__main__":
    main()