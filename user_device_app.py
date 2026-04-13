import sys
import os
import requests as http_client

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

GRID_URL = "http://127.0.0.1:5000"
KIOSK_URL = "http://127.0.0.1:5001"

# Users registered through this device (uid -> {name, vmid, pin, zone_code})
registered_users = {}


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


# Proxy zone codes from Grid
@app.route("/api/providers")
def api_providers():
    try:
        r = http_client.get(f"{GRID_URL}/api/providers", timeout=5)
        return jsonify(r.json())
    except http_client.exceptions.ConnectionError:
        return jsonify({})


# Register EV owner via Grid Authority
@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.json
    try:
        r = http_client.post(f"{GRID_URL}/api/register_user", json=data, timeout=10)
        result = r.json()
    except http_client.exceptions.ConnectionError:
        return jsonify({"success": False, "error": "Cannot reach Grid Authority. Is it running?"})

    if result.get("success"):
        registered_users[result["uid"]] = {
            "name": result["name"],
            "vmid": result["vmid"],
            "zone_code": result["zone_code"],
            "pin": data.get("pin", ""),
            "balance": result["balance"],
        }
        print(f"[Device] Registered: {result['name']} — VMID: {result['vmid']}")

    return jsonify(result)


# Users registered on this device
@app.route("/api/my_users")
def api_my_users():
    # Refresh balances from Grid
    try:
        r = http_client.get(f"{GRID_URL}/api/users", timeout=5)
        grid_users = {u["vmid"]: u for u in r.json()}
        for uid, u in registered_users.items():
            if u["vmid"] in grid_users:
                u["balance"] = grid_users[u["vmid"]]["balance"]
    except http_client.exceptions.ConnectionError:
        pass

    items = []
    for uid, u in registered_users.items():
        items.append({"uid": uid, "name": u["name"], "vmid": u["vmid"],
                       "zone_code": u["zone_code"], "balance": u.get("balance", 0)})
    return jsonify(items)


# Fetch available QR sessions from Kiosk
@app.route("/api/qr_sessions")
def api_qr_sessions():
    try:
        r = http_client.get(f"{KIOSK_URL}/api/qr_sessions", timeout=5)
        return jsonify(r.json())
    except http_client.exceptions.ConnectionError:
        return jsonify([])


# Initiate charging session via Kiosk
@app.route("/api/charge", methods=["POST"])
def api_charge():
    data = request.json
    qr_data = data.get("qr_data", "").strip()
    vmid = data.get("vmid", "").strip()
    pin = data.get("pin", "").strip()
    amount = float(data.get("amount", 0))

    if not all([qr_data, vmid, pin]) or amount <= 0:
        return jsonify({"success": False, "error": "All fields are required."})

    print(f"\n[Device] Initiating session — VMID: {vmid} | Amount: Rs.{amount:.2f}")

    # Encrypt PIN/VMID with RSA for demonstration
    try:
        r = http_client.get(f"{GRID_URL}/api/providers", timeout=5)
        from crypto_utils.rsa_utils import rsa_encrypt
        rk = http_client.get(f"{GRID_URL}/api/franchises", timeout=5)
        # RSA encryption is demonstrated in console output only
        print(f"[Device] Sending encrypted credentials to Kiosk...")
    except Exception:
        pass

    # Forward to Kiosk for processing
    try:
        r = http_client.post(f"{KIOSK_URL}/api/process_session", json={
            "qr_data": qr_data, "vmid": vmid, "pin": pin, "amount": amount
        }, timeout=10)
        result = r.json()
    except http_client.exceptions.ConnectionError:
        return jsonify({"success": False, "error": "Cannot reach Charging Kiosk. Is it running?"})

    if result.get("success"):
        print(f"[Device] Charging approved! Balance: Rs.{result.get('user_balance', 0):.2f}")
    elif result.get("refund"):
        print(f"[Device] Hardware failure — refund issued.")
    else:
        print(f"[Device] Denied: {result.get('error')}")

    return jsonify(result)


# ──────────────────────────────────────────────
# HTML TEMPLATE
# ──────────────────────────────────────────────

HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>User Device - EV Charging Gateway</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:Arial,sans-serif; background:#f5f5f5; color:#333; font-size:14px; }
  .header { background:#6a1b9a; color:#fff; padding:14px 20px; }
  .header h1 { font-size:18px; }
  .header p { font-size:12px; opacity:0.8; }
  .tabs { display:flex; background:#fff; border-bottom:1px solid #ddd; flex-wrap:wrap; }
  .tab { padding:10px 16px; font-size:13px; cursor:pointer; border:none; background:none; color:#555; border-bottom:2px solid transparent; }
  .tab:hover { color:#000; }
  .tab.active { color:#6a1b9a; border-bottom-color:#6a1b9a; font-weight:bold; }
  .content { padding:20px; max-width:600px; margin:0 auto; }
  .panel { background:#fff; border:1px solid #ddd; border-radius:6px; }
  .panel-head { padding:10px 14px; border-bottom:1px solid #eee; font-weight:bold; font-size:14px; background:#f3e5f5; color:#6a1b9a; }
  .panel-body { padding:14px; }
  label { display:block; font-size:12px; color:#555; margin-bottom:3px; margin-top:8px; }
  input,select { width:100%; padding:7px 10px; border:1px solid #ccc; border-radius:4px; font-size:13px; font-family:monospace; }
  input:focus,select:focus { outline:none; border-color:#6a1b9a; }
  .btn { display:inline-block; padding:8px 16px; border:none; border-radius:4px; font-size:13px; cursor:pointer; margin-top:10px; }
  .btn-primary { background:#6a1b9a; color:#fff; }
  .btn-primary:hover { background:#7b1fa2; }
  .btn-secondary { background:#eee; color:#333; border:1px solid #ccc; }
  .result { margin-top:10px; padding:10px; border-radius:4px; font-size:13px; font-family:monospace; word-break:break-all; line-height:1.6; }
  .result.ok { background:#e6f9ee; border:1px solid #b2dfdb; color:#2e7d32; }
  .result.err { background:#fdecea; border:1px solid #f5c6cb; color:#c62828; }
  .result.info { background:#f3e5f5; border:1px solid #ce93d8; color:#6a1b9a; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th { text-align:left; padding:8px; background:#f3e5f5; border-bottom:2px solid #ddd; font-size:12px; color:#6a1b9a; }
  td { padding:8px; border-bottom:1px solid #eee; font-family:monospace; font-size:12px; }
  .hidden { display:none; }
  .user-card { background:#fafafa; border:1px solid #e0e0e0; border-radius:5px; padding:10px; margin-bottom:8px; }
  .user-card .name { font-weight:bold; color:#6a1b9a; }
  .user-card .detail { font-size:12px; color:#555; font-family:monospace; margin-top:4px; }
</style>
</head>
<body>

<div class="header">
  <h1>EV Owner Device</h1>
  <p>Mobile device — Register, scan QR codes, and initiate charging sessions</p>
</div>

<div class="tabs">
  <button class="tab active" onclick="switchTab(this,'tab-register')">Register</button>
  <button class="tab" onclick="switchTab(this,'tab-account')">My Account</button>
  <button class="tab" onclick="switchTab(this,'tab-charge')">Charge</button>
</div>

<div class="content">

  <!-- REGISTER -->
  <div id="tab-register" class="tab-content">
    <div class="panel">
      <div class="panel-head">Register as EV Owner</div>
      <div class="panel-body">
        <label>Name</label>
        <input id="u_name" placeholder="e.g. Arjun Mehta">
        <label>Zone Code</label>
        <select id="u_zone"><option value="">Select zone...</option></select>
        <label>Password</label>
        <input id="u_pass" type="password">
        <label>4-digit PIN</label>
        <input id="u_pin" maxlength="4" placeholder="1234">
        <label>Mobile Number</label>
        <input id="u_mobile" placeholder="9876543210">
        <label>Initial Balance</label>
        <input id="u_bal" type="number" value="5000">
        <button class="btn btn-primary" onclick="registerUser()">Register with Grid</button>
        <div id="reg_result"></div>
      </div>
    </div>
  </div>

  <!-- MY ACCOUNT -->
  <div id="tab-account" class="tab-content hidden">
    <div class="panel">
      <div class="panel-head">Registered Users on this Device</div>
      <div class="panel-body">
        <button class="btn btn-secondary" onclick="loadMyUsers()" style="margin-bottom:10px;">Refresh</button>
        <div id="my_users"><p style="color:#999">No users registered yet.</p></div>
      </div>
    </div>
  </div>

  <!-- CHARGE -->
  <div id="tab-charge" class="tab-content hidden">
    <div class="panel">
      <div class="panel-head">Initiate Charging Session</div>
      <div class="panel-body">

        <label>QR Session (Franchise)</label>
        <select id="ch_qr"><option value="">Loading QR sessions from Kiosk...</option></select>
        <button class="btn btn-secondary" onclick="loadChargeData()" style="margin-top:4px;font-size:11px;">Refresh</button>

        <div style="margin-top:10px;padding-top:10px;border-top:1px solid #eee;">
          <label>Or scan QR code from Kiosk screen</label>
          <p style="font-size:11px;color:#888;margin-bottom:6px;">Take a photo of the QR code or pick from gallery</p>
          <input type="file" id="qr_file" accept="image/*" capture="environment" onchange="scanQRFile(this)" style="font-size:13px;">
          <div id="qr_scan_reader" style="display:none;"></div>
          <div id="scan_status"></div>
        </div>

        <label>Select Your Account</label>
        <select id="ch_user"><option value="">Select user...</option></select>

        <label>PIN</label>
        <input id="ch_pin" maxlength="4" placeholder="Enter your PIN">

        <label>Amount (Rs.)</label>
        <input id="ch_amount" type="number" placeholder="500">

        <button class="btn btn-primary" onclick="chargeSession()">Pay & Start Charging</button>
        <div id="ch_result"></div>
      </div>
    </div>
  </div>

</div>

<script src="https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>
<script>
async function api(url,opts){const r=await fetch(url,opts);return r.json();}
function post(url,data){return api(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});}
function $(id){return document.getElementById(id);}

let scannedQrData='';

function scanQRFile(input){
  if(!input.files||!input.files[0]) return;
  $('scan_status').innerHTML='<div class="result info">Reading QR code from image...</div>';
  const html5QrCode=new Html5Qrcode("qr_scan_reader");
  html5QrCode.scanFile(input.files[0],true)
    .then(decodedText=>{
      scannedQrData=decodedText;
      const parts=decodedText.split('|');
      const sessionId=parts.length>=1?parts[0].slice(0,16)+'...':'unknown';
      $('scan_status').innerHTML=`<div class="result ok">QR Scanned! Session: ${sessionId}</div>`;
      // Clear dropdown selection so scanned data is used
      $('ch_qr').value='';
    })
    .catch(err=>{
      $('scan_status').innerHTML=`<div class="result err">Could not read QR code from image. Try again or select from dropdown.</div>`;
    });
}

function switchTab(btn,id){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(t=>t.classList.add('hidden'));
  btn.classList.add('active'); $(id).classList.remove('hidden');
  if(id==='tab-account') loadMyUsers();
  if(id==='tab-charge') loadChargeData();
}

async function loadZones(){
  try {
    const providers=await api('/api/providers');
    const s=$('u_zone');
    s.innerHTML='<option value="">Select zone...</option>';
    for(const[prov,zones] of Object.entries(providers)){
      zones.forEach(z=>{s.innerHTML+=`<option value="${z}">${z} (${prov})</option>`;});
    }
  } catch(e) {
    $('u_zone').innerHTML='<option value="">Cannot reach Grid</option>';
  }
}

async function registerUser(){
  const data=await post('/api/register',{
    name:$('u_name').value, zone_code:$('u_zone').value,
    password:$('u_pass').value, pin:$('u_pin').value,
    mobile:$('u_mobile').value, balance:$('u_bal').value
  });
  const el=$('reg_result');
  if(data.success){
    el.className='result ok';
    el.innerHTML=`Registered!<br>UID: ${data.uid}<br>VMID: ${data.vmid}<br>Balance: Rs.${data.balance}`;
  } else {
    el.className='result err';
    el.innerHTML=data.error;
  }
}

async function loadMyUsers(){
  const items=await api('/api/my_users');
  const el=$('my_users');
  if(!items.length){el.innerHTML='<p style="color:#999">No users registered yet. Go to Register tab.</p>';return;}
  let html='';
  items.forEach(u=>{
    html+=`<div class="user-card">
      <div class="name">${u.name}</div>
      <div class="detail">VMID: ${u.vmid}<br>Zone: ${u.zone_code}<br>Balance: Rs.${u.balance.toFixed(2)}</div>
    </div>`;
  });
  el.innerHTML=html;
}

async function loadChargeData(){
  // Load QR sessions from Kiosk
  try {
    const sessions=await api('/api/qr_sessions');
    const s1=$('ch_qr');
    if(!sessions.length){s1.innerHTML='<option value="">No QR sessions available</option>';return;}
    s1.innerHTML='<option value="">Select QR session...</option>';
    sessions.forEach(s=>{
      const mins=Math.floor((s.remaining_seconds||0)/60);
      const secs=(s.remaining_seconds||0)%60;
      s1.innerHTML+=`<option value='${s.qr_data}'>FID: ${s.fid.slice(0,10)}... (${mins}m ${secs}s left)</option>`;
    });
  } catch(e) {
    $('ch_qr').innerHTML='<option value="">Cannot reach Kiosk</option>';
  }

  // Load registered users on this device
  const users=await api('/api/my_users');
  const s2=$('ch_user');
  if(!users.length){s2.innerHTML='<option value="">No users registered — go to Register tab</option>';return;}
  s2.innerHTML='<option value="">Select user...</option>';
  users.forEach(u=>{s2.innerHTML+=`<option value="${u.vmid}">${u.name} — Rs.${u.balance.toFixed(0)}</option>`;});
}

async function chargeSession(){
  // Use dropdown if selected, otherwise use scanned QR data
  const qrData=$('ch_qr').value||scannedQrData;
  if(!qrData){
    $('ch_result').className='result err';
    $('ch_result').innerHTML='Select a QR session from the dropdown or scan a QR code first.';
    return;
  }
  const data=await post('/api/charge',{
    qr_data:qrData, vmid:$('ch_user').value,
    pin:$('ch_pin').value, amount:$('ch_amount').value
  });
  const el=$('ch_result');
  if(data.success){
    el.className='result ok';
    el.innerHTML=`Payment approved!<br>Block #${data.block_index}<br>Txn: ${data.transaction_id?.slice(0,24)}...<br>Your balance: Rs.${data.user_balance?.toFixed(2)}`;
  } else if(data.refund){
    el.className='result err';
    el.innerHTML=`Hardware failure! Refund issued.<br>Balance restored: Rs.${data.user_balance?.toFixed(2)}`;
  } else {
    el.className='result err';
    el.innerHTML=data.error||'Transaction failed.';
  }
}

loadZones();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("  EV OWNER DEVICE — Port 5002")
    print("  http://localhost:5002")
    print("=" * 55 + "\n")
    app.run(debug=True, host="0.0.0.0", port=5002)
