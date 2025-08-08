from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import subprocess
import ctypes
import time

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this in production

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_powershell_command(command):
    try:
        # Create a process with elevated privileges
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        # Run the command and capture output
        process = subprocess.Popen(
            ['powershell', '-Command', command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=startupinfo,
            text=True
        )
        
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            print(f"PowerShell Error: {stderr}")
            raise Exception(f"PowerShell command failed: {stderr}")
            
        return stdout.strip()
    except Exception as e:
        print(f"Error running PowerShell command: {str(e)}")
        raise

def get_usb_status():
    try:
        # Get enabled USB devices (excluding system devices)
        command = "Get-PnpDevice -Class USB | Where-Object {$_.FriendlyName -notlike '*USB Root Hub*' -and $_.FriendlyName -notlike '*USB Composite Device*'} | Where-Object {$_.Status -eq 'OK'} | Measure-Object | Select-Object -ExpandProperty Count"
        enabled = int(run_powershell_command(command) or 0)
        
        # Get total USB devices (excluding system devices)
        command = "Get-PnpDevice -Class USB | Where-Object {$_.FriendlyName -notlike '*USB Root Hub*' -and $_.FriendlyName -notlike '*USB Composite Device*'} | Measure-Object | Select-Object -ExpandProperty Count"
        total = int(run_powershell_command(command) or 0)
        
        return {
            'enabled': enabled,
            'total': total,
            'status': 'Enabled' if enabled == total else 'Partially Enabled' if enabled > 0 else 'Disabled'
        }
    except Exception as e:
        print(f"Error getting USB status: {str(e)}")
        return {'enabled': 0, 'total': 0, 'status': 'Error'}

def set_all_usb_state(enable):
    if not is_admin():
        raise PermissionError("Administrator privileges are required")
        
    try:
        # First, get all USB device IDs that are not system devices
        command = "Get-PnpDevice -Class USB | Where-Object {$_.FriendlyName -notlike '*USB Root Hub*' -and $_.FriendlyName -notlike '*USB Composite Device*'} | Select-Object -ExpandProperty InstanceId"
        device_ids = run_powershell_command(command).split('\n')
        
        success_count = 0
        failed_devices = []
        
        for device_id in device_ids:
            if not device_id.strip():
                continue
                
            try:
                # First try to stop any processes using the device
                stop_command = f'Get-PnpDevice -InstanceId "{device_id}" | Get-PnpDeviceProperty -KeyName "DEVPKEY_Device_IsPresent" | Select-Object -ExpandProperty Data'
                is_present = run_powershell_command(stop_command)
                
                if is_present == "True":
                    # Enable/disable individual device with error handling
                    if enable:
                        command = f'Enable-PnpDevice -InstanceId "{device_id}" -Confirm:$false -ErrorAction Stop'
                    else:
                        command = f'Disable-PnpDevice -InstanceId "{device_id}" -Confirm:$false -ErrorAction Stop'
                    
                    try:
                        run_powershell_command(command)
                        success_count += 1
                        time.sleep(0.5)  # Increased delay between operations
                    except Exception as e:
                        failed_devices.append(device_id)
                        print(f"Failed to {'enable' if enable else 'disable'} device {device_id}: {str(e)}")
                        continue
                
            except Exception as e:
                print(f"Error processing device {device_id}: {str(e)}")
                failed_devices.append(device_id)
                continue
        
        # Get updated status
        usb_status = get_usb_status()
        
        message = f"Successfully {'enabled' if enable else 'disabled'} {success_count} USB devices"
        if failed_devices:
            message += f". Failed to process {len(failed_devices)} devices."
        
        return {
            'success': success_count > 0,
            'message': message,
            'failed_devices': failed_devices
        }
    except Exception as e:
        print(f"Error setting USB state: {str(e)}")
        raise

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'password123':
            session['user'] = username
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('index.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    if not is_admin():
        flash('Warning: Administrator privileges are required', 'warning')
    
    usb_status = get_usb_status()
    
    if request.method == 'POST':
        action = request.form['action']
        enable = action == 'enable'
        try:
            result = set_all_usb_state(enable)
            if result['success']:
                flash(result['message'], 'success')
            else:
                flash('No USB devices were affected', 'info')
            if result.get('failed_devices'):
                flash(f'Some devices could not be processed. Please try again or check device manager.', 'warning')
        except PermissionError as e:
            flash('Error: Administrator privileges are required', 'danger')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))
    
    return render_template('dashboard.html', usb_status=usb_status)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    if not is_admin():
        print("Warning: Running without administrator privileges. USB control operations may fail.")
    app.run(host='0.0.0.0', port=5000, debug=True)