import sys
import os
import time
import base64
import requests as http_client

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template_string, request, jsonify, send_from_directory
from entities.charging_kiosk import ChargingKiosk
from config import QR_CODE_DIR

app = Flask(__name__)
kiosk = ChargingKiosk()
qr_sessions = {}

GRID_URL = "http://127.0.0.1:5000"


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


# Proxy franchise list from Grid Authority
@app.route("/api/franchises")
def api_franchises():
    try:
        r = http_client.get(f"{GRID_URL}/api/franchises", timeout=5)
        return jsonify(r.json())
    except http_client.exceptions.ConnectionError:
        return jsonify([])


# Encrypt FID with ASCON and generate QR code
@app.route("/api/generate_qr", methods=["POST"])
def api_generate_qr():
    data = request.json
    fid = data.get("fid", "").strip()

    if not fid:
        return jsonify({"success": False, "error": "Franchise ID is required."})

    try:
        r = http_client.get(f"{GRID_URL}/api/franchises", timeout=5)
        franchises = {f["fid"]: f for f in r.json()}
    except http_client.exceptions.ConnectionError:
        return jsonify({"success": False, "error": "Cannot reach Grid Authority. Is it running?"})

    if fid not in franchises:
        return jsonify({"success": False, "error": "Franchise not found on Grid."})

    fname = franchises[fid]["name"]
    result = kiosk.generate_vfid_and_qr(fid, fname)
    qr_sessions[result["session_id"]] = result

    # Read QR image and encode as base64 for display in UI
    qr_image_b64 = ""
    qr_path = result.get("qr_path", "")
    if qr_path and os.path.exists(qr_path) and qr_path.endswith(".png"):
        with open(qr_path, "rb") as f:
            qr_image_b64 = base64.b64encode(f.read()).decode("utf-8")

    return jsonify({
        "success": True,
        "session_id": result["session_id"],
        "vfid": result["vfid"],
        "qr_data": result["qr_data"],
        "franchise_name": fname,
        "qr_image": qr_image_b64,
    })


# List all active QR sessions
@app.route("/api/qr_sessions")
def api_qr_sessions():
    items = []
    for sid, s in qr_sessions.items():
        fid = kiosk.active_sessions.get(sid, {}).get("fid", "?")
        items.append({
            "session_id": sid,
            "fid": fid,
            "vfid": s["vfid"],
            "qr_data": s["qr_data"],
        })
    return jsonify(items)


# Decrypt QR and forward transaction to Grid
@app.route("/api/process_session", methods=["POST"])
def api_process_session():
    data = request.json
    qr_data = data.get("qr_data", "").strip()
    vmid = data.get("vmid", "").strip()
    pin = data.get("pin", "").strip()
    amount = float(data.get("amount", 0))

    if not all([qr_data, vmid, pin]) or amount <= 0:
        return jsonify({"success": False, "error": "All fields are required."})

    print(f"\n[Kiosk] Processing session — VMID: {vmid} | Amount: Rs.{amount:.2f}")

    # Decrypt QR to recover FID using ASCON
    fid = kiosk.decrypt_qr(qr_data)
    if fid is None:
        return jsonify({"success": False, "error": "Failed to decrypt QR code."})

    # Forward to Grid Authority for transaction processing
    try:
        print(f"[Kiosk] Forwarding to Grid Authority — FID: {fid}")
        r = http_client.post(f"{GRID_URL}/api/process_transaction", json={
            "fid": fid, "vmid": vmid, "pin": pin, "amount": amount
        }, timeout=10)
        result = r.json()
    except http_client.exceptions.ConnectionError:
        return jsonify({"success": False, "error": "Cannot reach Grid Authority. Is it running?"})

    if result.get("success"):
        print(f"[Kiosk] Grid approved transaction.")
    elif result.get("refund"):
        print(f"[Kiosk] Hardware failure — refund processed.")
    else:
        print(f"[Kiosk] Grid rejected: {result.get('error')}")

    return jsonify(result)


# Serve QR code images from the qr_codes directory
@app.route("/qr_codes/<path:filename>")
def serve_qr(filename):
    return send_from_directory(QR_CODE_DIR, filename)


# ──────────────────────────────────────────────
# HTML TEMPLATE
# ──────────────────────────────────────────────

HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Charging Kiosk - EV Charging Gateway</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:Arial,sans-serif; background:#f5f5f5; color:#333; font-size:14px; }
  .header { background:#2e7d32; color:#fff; padding:14px 20px; }
  .header h1 { font-size:18px; }
  .header p { font-size:12px; opacity:0.8; }
  .content { padding:20px; max-width:1100px; margin:0 auto; }
  .panel-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(340px,1fr)); gap:16px; }
  .panel { background:#fff; border:1px solid #ddd; border-radius:6px; }
  .panel-head { padding:10px 14px; border-bottom:1px solid #eee; font-weight:bold; font-size:14px; background:#e8f5e9; color:#2e7d32; }
  .panel-body { padding:14px; }
  label { display:block; font-size:12px; color:#555; margin-bottom:3px; margin-top:8px; }
  select { width:100%; padding:7px 10px; border:1px solid #ccc; border-radius:4px; font-size:13px; font-family:monospace; }
  select:focus { outline:none; border-color:#2e7d32; }
  .btn { display:inline-block; padding:8px 16px; border:none; border-radius:4px; font-size:13px; cursor:pointer; margin-top:10px; }
  .btn-primary { background:#2e7d32; color:#fff; }
  .btn-primary:hover { background:#388e3c; }
  .btn-secondary { background:#eee; color:#333; border:1px solid #ccc; }
  .result { margin-top:10px; padding:10px; border-radius:4px; font-size:13px; font-family:monospace; word-break:break-all; line-height:1.6; }
  .result.ok { background:#e6f9ee; border:1px solid #b2dfdb; color:#2e7d32; }
  .result.err { background:#fdecea; border:1px solid #f5c6cb; color:#c62828; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th { text-align:left; padding:8px; background:#e8f5e9; border-bottom:2px solid #ddd; font-size:12px; color:#2e7d32; }
  td { padding:8px; border-bottom:1px solid #eee; font-family:monospace; font-size:12px; }
  .entity-badge { display:inline-block; background:#fff; color:#2e7d32; padding:2px 10px; border-radius:12px; font-size:11px; margin-left:10px; font-weight:bold; }
  .detail-box { background:#f5f5f5; border:1px solid #e0e0e0; border-radius:5px; padding:12px; margin-top:10px; font-size:12px; font-family:monospace; line-height:1.8; }
</style>
</head>
<body>

<div class="header">
  <h1>Charging Kiosk Terminal <span class="entity-badge">Entity 2</span></h1>
  <p>Physical kiosk at the charging station — Generates encrypted QR codes, processes sessions</p>
</div>

<div class="content">
  <div class="panel-grid">

    <div class="panel">
      <div class="panel-head">Generate QR Code (ASCON-128 Encryption)</div>
      <div class="panel-body">
        <label>Select Franchise</label>
        <select id="qr_fid"><option value="">Loading franchises from Grid...</option></select>
        <button class="btn btn-primary" onclick="generateQR()">Encrypt FID & Generate QR</button>
        <button class="btn btn-secondary" onclick="loadFranchises()" style="margin-left:6px;">Refresh</button>
        <div id="qr_result"></div>
      </div>
    </div>

    <div class="panel">
      <div class="panel-head">Active QR Sessions</div>
      <div class="panel-body" id="sessions_list">
        <p style="color:#999">No sessions yet. Generate a QR code first.</p>
      </div>
    </div>

  </div>
</div>

<script>
async function api(url,opts){const r=await fetch(url,opts);return r.json();}
function post(url,data){return api(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});}
function $(id){return document.getElementById(id);}

async function loadFranchises(){
  try {
    const items=await api('/api/franchises');
    const s=$('qr_fid');
    if(!items.length){s.innerHTML='<option value="">No franchises registered on Grid</option>';return;}
    s.innerHTML='<option value="">Select franchise...</option>';
    items.forEach(f=>{s.innerHTML+=`<option value="${f.fid}">${f.name} (${f.zone_code})</option>`;});
  } catch(e) {
    $('qr_fid').innerHTML='<option value="">Cannot reach Grid Authority</option>';
  }
}

async function generateQR(){
  const fid=$('qr_fid').value;
  if(!fid){$('qr_result').className='result err';$('qr_result').innerHTML='Select a franchise first.';return;}
  const data=await post('/api/generate_qr',{fid});
  const el=$('qr_result');
  if(data.success){
    el.className='result ok';
    let html=`QR generated for <b>${data.franchise_name}</b><br>Session: ${data.session_id.slice(0,16)}...<br>VFID (encrypted): ${data.vfid}`;
    if(data.qr_image){
      html+=`<div style="margin-top:12px;text-align:center;"><img src="data:image/png;base64,${data.qr_image}" alt="QR Code" style="max-width:200px;border:1px solid #ccc;border-radius:4px;"></div>`;
    }
    el.innerHTML=html;
  } else {
    el.className='result err';
    el.innerHTML=data.error;
  }
  loadSessions();
}

async function loadSessions(){
  const items=await api('/api/qr_sessions');
  const el=$('sessions_list');
  if(!items.length){el.innerHTML='<p style="color:#999">No sessions yet.</p>';return;}
  let html='<table><thead><tr><th>Session ID</th><th>FID</th><th>VFID</th></tr></thead><tbody>';
  items.forEach(s=>{html+=`<tr><td>${s.session_id.slice(0,12)}...</td><td>${s.fid.slice(0,12)}...</td><td>${s.vfid.slice(0,12)}...</td></tr>`;});
  el.innerHTML=html+'</tbody></table>';
}

loadFranchises();
loadSessions();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("  CHARGING KIOSK TERMINAL — Port 5001")
    print("  http://localhost:5001")
    print("=" * 55 + "\n")
    app.run(debug=True, host="127.0.0.1", port=5001)
