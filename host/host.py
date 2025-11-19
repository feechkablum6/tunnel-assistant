import sys
import json
import struct
import os
import random
import string
import subprocess
import time

# Windows Native Messaging setup
def get_message():
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length:
        sys.exit(0)
    message_length = struct.unpack('=I', raw_length)[0]
    message = sys.stdin.buffer.read(message_length).decode("utf-8")
    return json.loads(message)

def send_message(message):
    encoded_content = json.dumps(message).encode("utf-8")
    encoded_length = struct.pack('=I', len(encoded_content))
    sys.stdout.buffer.write(encoded_length)
    sys.stdout.buffer.write(encoded_content)
    sys.stdout.buffer.flush()

def generate_id():
    return 'ruleItem-' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))

def kill_and_restart_app(app_path):
    # Kill process
    subprocess.run(["taskkill", "/F", "/IM", "TunnlTo.exe"], capture_output=True)
    time.sleep(1) # Wait for file release
    
    # Restart process (detached)
    # We need to find where TunnlTo.exe is installed. 
    # Usually in Local AppData.
    if not app_path:
        # Check Program Files (Standard installation)
        program_files = os.environ.get('ProgramFiles', 'C:\\Program Files')
        possible_path = os.path.join(program_files, "TunnlTo", "TunnlTo.exe")
        if os.path.exists(possible_path):
            app_path = possible_path
        else:
            # Check Local AppData (User installation)
            local_app_data = os.environ.get('LOCALAPPDATA', '')
            possible_path_local = os.path.join(local_app_data, "TunnlTo", "TunnlTo.exe")
            if os.path.exists(possible_path_local):
                app_path = possible_path_local

    if app_path and os.path.exists(app_path):
        subprocess.Popen([app_path], close_fds=True)
        return True
    return False

def main():
    while True:
        try:
            msg = get_message()
            if msg.get('action') == 'addRule':
                domain = msg.get('domain')
                ip = msg.get('ip')
                rule_type = msg.get('type')
                
                app_data_path = os.path.join(os.environ['APPDATA'], 'com.tunnl.to')
                rules_file = os.path.join(app_data_path, 'rule_items_store.json')
                app_data_file = os.path.join(app_data_path, 'app_data_store.json')
                
                # 1. KILL APP FIRST to prevent overwrite on exit
                # We try to find the exe path. It's often in LocalAppData/TunnlTo/TunnlTo.exe
                local_app_data = os.environ['LOCALAPPDATA']
                exe_path = os.path.join(local_app_data, "TunnlTo", "TunnlTo.exe")
                
                # Kill it gracefully first
                subprocess.run(["taskkill", "/IM", "TunnlTo.exe"], capture_output=True)
                time.sleep(1)
                # Force kill if still running
                subprocess.run(["taskkill", "/F", "/IM", "TunnlTo.exe"], capture_output=True)
                time.sleep(0.5)
                
                if not os.path.exists(rules_file) or not os.path.exists(app_data_file):
                     send_message({"status": "error", "message": "Config files not found"})
                     continue

                # 2. Modify Rules
                with open(rules_file, 'r') as f:
                    rules_data = json.load(f)
                
                existing_id = None
                for rid, rdata in rules_data.get('ruleItems', {}).items():
                    if rdata.get('value') == ip:
                        existing_id = rid
                        break
                
                if existing_id:
                    rule_id = existing_id
                    status = "Rule updated"
                else:
                    rule_id = generate_id()
                    while rule_id in rules_data.get('ruleItems', {}):
                        rule_id = generate_id()
                        
                    new_rule = {
                        "id": rule_id,
                        "name": domain,
                        "type": rule_type,
                        "value": ip
                    }
                    rules_data.setdefault('ruleItems', {})[rule_id] = new_rule
                    with open(rules_file, 'w') as f:
                        json.dump(rules_data, f, indent=2)
                    status = "Rule created"

                # 2.5. Force Auto-Connect Settings
                settings_file = os.path.join(app_data_path, 'settings_store.json')
                if os.path.exists(settings_file):
                    with open(settings_file, 'r') as f:
                        settings_data = json.load(f)
                    
                    # Force settings to minimize
                    changed_settings = False
                    if settings_data.get('settings', {}).get('minimizeOnStart') != True:
                        settings_data.setdefault('settings', {})['minimizeOnStart'] = True
                        changed_settings = True
                        
                    if changed_settings:
                        with open(settings_file, 'w') as f:
                            json.dump(settings_data, f, indent=2)

                # 3. Modify Active List
                with open(app_data_file, 'r') as f:
                    app_config = json.load(f)
                
                tunnel_state = app_config.get('appData', {}).get('enableTunnelState', {})
                
                # Force enableOnSystemStart
                if tunnel_state.get('enableOnSystemStart') != True:
                    tunnel_state['enableOnSystemStart'] = True
                    # We need to save this back
                
                allowed = tunnel_state.get('allowed', {}).get('itemIds', [])
                disallowed = tunnel_state.get('disallowed', {}).get('itemIds', [])
                
                # Determine active list
                target_list = None
                if len(disallowed) > 0:
                    target_list = disallowed
                elif len(allowed) > 0:
                    target_list = allowed
                else:
                    target_list = allowed # Default
                
                if rule_id not in target_list:
                    target_list.append(rule_id)
                
                # Save App Data
                with open(app_data_file, 'w') as f:
                    json.dump(app_config, f, indent=2)
                
                # 4. Restart App
                # We resolve the path again or use the one we found
                program_files = os.environ.get('ProgramFiles', 'C:\\Program Files')
                exe_path = os.path.join(program_files, "TunnlTo", "TunnlTo.exe")
                
                if not os.path.exists(exe_path):
                     local_app_data = os.environ.get('LOCALAPPDATA', '')
                     exe_path = os.path.join(local_app_data, "TunnlTo", "TunnlTo.exe")

                if os.path.exists(exe_path):
                    # Use STARTUPINFO to start minimized
                    si = subprocess.STARTUPINFO()
                    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    si.wShowWindow = 7 # SW_SHOWMINNOACTIVE (Minimizes without activating)
                    
                    subprocess.Popen([exe_path], close_fds=True, startupinfo=si, creationflags=subprocess.DETACHED_PROCESS if sys.platform == 'win32' else 0)
                    status += " & App Restarted (Hidden)"
                else:
                    status += " (Could not find TunnlTo.exe to restart)"

                send_message({"status": "success", "message": status})
            
            elif msg.get('action') == 'checkRule':
                ip = msg.get('ip')
                app_data_path = os.path.join(os.environ['APPDATA'], 'com.tunnl.to')
                rules_file = os.path.join(app_data_path, 'rule_items_store.json')
                
                if not os.path.exists(rules_file):
                    send_message({"exists": False})
                    continue
                    
                with open(rules_file, 'r') as f:
                    rules_data = json.load(f)
                
                found = False
                for rid, rdata in rules_data.get('ruleItems', {}).items():
                    if rdata.get('value') == ip:
                        send_message({"exists": True, "rule": rdata})
                        found = True
                        break
                
                if not found:
                    send_message({"exists": False})

            else:
                 send_message({"status": "error", "message": "Unknown action"})
        except Exception as e:
            send_message({"status": "error", "message": str(e)})

if __name__ == '__main__':
    main()
