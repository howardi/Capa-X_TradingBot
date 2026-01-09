#!/usr/bin/env python3
import os, subprocess, sys, time, threading

def read_output(pipe, prefix):
    for line in iter(pipe.readline, ''):
        print(f"[{prefix}] {line.strip()}")
    pipe.close()

def main():
    print("🚀 Starting services (SSH Tunnel)...")
    
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

    # 2. Start SSH Tunnel (Serveo)
    # ssh -o StrictHostKeyChecking=no -R 80:localhost:8501 serveo.net
    ssh_cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-R", "80:localhost:8501", "serveo.net"]
    
    # SSH usually prints URL to stdout or stderr. Serveo prints to stdout.
    ssh_proc = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    t_ssh_out = threading.Thread(target=read_output, args=(ssh_proc.stdout, "SSH"))
    t_ssh_err = threading.Thread(target=read_output, args=(ssh_proc.stderr, "SSH_Err"))
    t_ssh_out.daemon = True
    t_ssh_err.daemon = True
    t_ssh_out.start()
    t_ssh_err.start()

    print("✅ Services started. Press Ctrl+C to stop.")
    
    try:
        while True:
            time.sleep(1)
            if st_proc.poll() is not None:
                print("❌ Streamlit exited!")
                break
            if ssh_proc.poll() is not None:
                print("❌ SSH Tunnel exited!")
                break
    except KeyboardInterrupt:
        print("\n🛑 Stopping...")
        st_proc.terminate()
        ssh_proc.terminate()

if __name__ == "__main__":
    main()