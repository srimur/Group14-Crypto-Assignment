import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template_string, request, jsonify
from entities.grid_authority import GridAuthority
from entities.franchise import Franchise
from entities.ev_owner import EVOwner
from entities.charging_kiosk import ChargingKiosk
from crypto_utils.shor_simulation import shor_factor
from config import ENERGY_PROVIDERS, VALID_ZONE_CODES

app = Flask(__name__)

grid = GridAuthority()
kiosk = ChargingKiosk()
qr_sessions = {}


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/providers")
def get_providers():
    return jsonify(ENERGY_PROVIDERS)


@app.route("/api/register_franchise", methods=["POST"])
def api_register_franchise():
    data = request.json
    name = data.get("name", "").strip()
    zone = data.get("zone_code", "").strip()
    password = data.get("password", "").strip()
    balance = float(data.get("balance", 10000))

    if not name or not zone or not password:
        return jsonify({"success": False, "error": "All fields are required."})

    f = Franchise(name, zone, password, balance)
    result = f.register(grid)
    return jsonify(result)


@app.route("/api/register_user", methods=["POST"])
def api_register_user():
    data = request.json
    name = data.get("name", "").strip()
    zone = data.get("zone_code", "").strip()
    password = data.get("password", "").strip()
    pin = data.get("pin", "").strip()
    mobile = data.get("mobile", "").strip()
    balance = float(data.get("balance", 5000))

    if not all([name, zone, password, pin, mobile]):
        return jsonify({"success": False, "error": "All fields are required."})

    u = EVOwner(name, zone, password, pin, mobile, balance)
    result = u.register(grid)
    return jsonify(result)


@app.route("/api/franchises")
def api_franchises():
    items = []
    for fid, f in grid.franchises.items():
        items.append({
            "fid": fid, "name": f["name"],
            "zone_code": f["zone_code"],
            "balance": f["balance"], "active": f["active"]
        })
    return jsonify(items)


@app.route("/api/users")
def api_users():
    items = []
    for uid, u in grid.users.items():
        items.append({
            "uid": uid, "name": u["name"],
            "vmid": u["vmid"], "zone_code": u["zone_code"],
            "balance": u["balance"], "active": u["active"]
        })
    return jsonify(items)


@app.route("/api/generate_qr", methods=["POST"])
def api_generate_qr():
    data = request.json
    fid = data.get("fid", "").strip()
    if fid not in grid.franchises:
        return jsonify({"success": False, "error": "Franchise not found."})

    fname = grid.franchises[fid]["name"]
    result = kiosk.generate_vfid_and_qr(fid, fname)
    qr_sessions[result["session_id"]] = result
    return jsonify({
        "success": True,
        "session_id": result["session_id"],
        "vfid": result["vfid"],
        "qr_data": result["qr_data"],
        "franchise_name": fname,
    })


@app.route("/api/qr_sessions")
def api_qr_sessions():
    items = []
    for sid, s in qr_sessions.items():
        fid = kiosk.active_sessions.get(sid, {}).get("fid", "?")
        fname = grid.franchises.get(fid, {}).get("name", "Unknown")
        items.append({
            "session_id": sid,
            "franchise_name": fname,
            "vfid": s["vfid"],
            "qr_data": s["qr_data"],
        })
    return jsonify(items)


@app.route("/api/charge", methods=["POST"])
def api_charge():
    data = request.json
    qr_data = data.get("qr_data", "").strip()
    vmid = data.get("vmid", "").strip()
    pin = data.get("pin", "").strip()
    amount = float(data.get("amount", 0))

    if not all([qr_data, vmid, pin]) or amount <= 0:
        return jsonify({"success": False, "error": "All fields are required."})

    result = kiosk.process_session(qr_data, vmid, pin, amount, grid)
    return jsonify(result)


@app.route("/api/blockchain")
def api_blockchain():
    blocks = []
    for b in grid.blockchain.chain:
        blocks.append({
            "index": b.index,
            "transaction_id": b.transaction_id,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(b.timestamp)),
            "uid": b.transaction_data.get("uid", ""),
            "fid": b.transaction_data.get("fid", ""),
            "amount": b.transaction_data.get("amount", 0),
            "description": b.transaction_data.get("description", ""),
            "dispute": b.dispute_flag,
            "prev_hash": b.previous_hash,
            "hash": b.hash,
        })
    return jsonify(blocks)


@app.route("/api/validate_chain")
def api_validate_chain():
    is_valid, msg = grid.blockchain.validate_chain()
    return jsonify({"valid": is_valid, "message": msg})


@app.route("/api/shor")
def api_shor():
    keys = grid.get_rsa_keys()
    e, n = keys["public"]
    d, _ = keys["private"]
    real_p, real_q = keys["p"], keys["q"]

    start = time.time()
    p_found, q_found = shor_factor(n, verbose=False)
    elapsed = time.time() - start

    recovered = False
    d_recovered = None
    if p_found * q_found == n and p_found != 1 and q_found != 1:
        from sympy import mod_inverse
        phi = (p_found - 1) * (q_found - 1)
        try:
            d_recovered = int(mod_inverse(e, phi))
            recovered = True
        except Exception:
            pass

    return jsonify({
        "e": e, "n": n, "real_p": real_p, "real_q": real_q,
        "p_found": p_found, "q_found": q_found,
        "d_original": d, "d_recovered": d_recovered,
        "key_recovered": recovered,
        "match": d == d_recovered if recovered else False,
        "elapsed": round(elapsed, 4),
    })


@app.route("/api/run_demo", methods=["POST"])
def api_run_demo():
    global qr_sessions
    log = []

    f1 = Franchise("Tata EV Hub", "TP-NORTH", "tata@secure123", 50000.0)
    r = f1.register(grid)
    log.append({"step": "Register Franchise", "detail": f"Tata EV Hub → FID: {r.get('fid','FAILED')}", "success": r["success"]})

    f2 = Franchise("Adani ChargeZone", "AD-SOUTH", "adani@pass456", 75000.0)
    r = f2.register(grid)
    log.append({"step": "Register Franchise", "detail": f"Adani ChargeZone → FID: {r.get('fid','FAILED')}", "success": r["success"]})

    f3 = Franchise("ChargePoint Express", "CP-ZONE1", "cp@key789", 60000.0)
    r = f3.register(grid)
    log.append({"step": "Register Franchise", "detail": f"ChargePoint Express → FID: {r.get('fid','FAILED')}", "success": r["success"]})

    u1 = EVOwner("Arjun Mehta", "TP-NORTH", "arjun@pw1", "1234", "9876543210", 3000.0)
    r = u1.register(grid)
    log.append({"step": "Register User", "detail": f"Arjun Mehta → VMID: {r.get('vmid','FAILED')}", "success": r["success"]})

    u2 = EVOwner("Priya Sharma", "AD-SOUTH", "priya@pw2", "5678", "9123456789", 5000.0)
    r = u2.register(grid)
    log.append({"step": "Register User", "detail": f"Priya Sharma → VMID: {r.get('vmid','FAILED')}", "success": r["success"]})

    u3 = EVOwner("Rahul Verma", "CP-ZONE1", "rahul@pw3", "9999", "9988776655", 1500.0)
    r = u3.register(grid)
    log.append({"step": "Register User", "detail": f"Rahul Verma → VMID: {r.get('vmid','FAILED')}", "success": r["success"]})

    qr1 = kiosk.generate_vfid_and_qr(f1.fid, f1.name)
    qr_sessions[qr1["session_id"]] = qr1
    log.append({"step": "Generate QR", "detail": f"Tata EV Hub → VFID: {qr1['vfid'][:16]}…", "success": True})

    qr2 = kiosk.generate_vfid_and_qr(f2.fid, f2.name)
    qr_sessions[qr2["session_id"]] = qr2
    log.append({"step": "Generate QR", "detail": f"Adani ChargeZone → VFID: {qr2['vfid'][:16]}…", "success": True})

    qr3 = kiosk.generate_vfid_and_qr(f3.fid, f3.name)
    qr_sessions[qr3["session_id"]] = qr3
    log.append({"step": "Generate QR", "detail": f"ChargePoint Express → VFID: {qr3['vfid'][:16]}…", "success": True})

    r = u1.initiate_session(qr1["qr_data"], 500.0, kiosk, grid)
    log.append({"step": "Charge Session", "detail": f"Arjun @ Tata ₹500", "success": r["success"]})

    r = u2.initiate_session(qr2["qr_data"], 800.0, kiosk, grid)
    log.append({"step": "Charge Session", "detail": f"Priya @ Adani ₹800", "success": r["success"]})

    r = u3.initiate_session(qr3["qr_data"], 2000.0, kiosk, grid)
    log.append({"step": "Charge Session", "detail": f"Rahul @ ChargePoint ₹2000 (insufficient)", "success": r["success"]})

    u1_wrong = EVOwner("Arjun Mehta", "TP-NORTH", "", "0000", "9876543210")
    u1_wrong.uid = u1.uid
    u1_wrong.vmid = u1.vmid
    r = u1_wrong.initiate_session(qr1["qr_data"], 100.0, kiosk, grid)
    log.append({"step": "Charge Session", "detail": f"Arjun wrong PIN ₹100", "success": r["success"]})

    r = u3.initiate_session(qr3["qr_data"], 500.0, kiosk, grid)
    log.append({"step": "Charge Session", "detail": f"Rahul @ ChargePoint ₹500", "success": r["success"]})

    return jsonify({"log": log})


HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EV Charging Payment Gateway</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: Arial, sans-serif; background: #f5f5f5; color: #333; font-size: 14px; }

  .header { background: #fff; border-bottom: 1px solid #ddd; padding: 12px 20px; }
  .header h1 { font-size: 18px; }
  .header p { font-size: 12px; color: #777; }
  .header-row { display: flex; justify-content: space-between; align-items: center; }

  .tabs { display: flex; background: #fff; border-bottom: 1px solid #ddd; flex-wrap: wrap; }
  .tab {
    padding: 10px 16px; font-size: 13px; cursor: pointer;
    border: none; background: none; color: #555;
    border-bottom: 2px solid transparent;
  }
  .tab:hover { color: #000; }
  .tab.active { color: #0066cc; border-bottom-color: #0066cc; font-weight: bold; }

  .content { padding: 20px; max-width: 1100px; margin: 0 auto; }
  .panel-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }

  .panel { background: #fff; border: 1px solid #ddd; border-radius: 6px; }
  .panel-head { padding: 10px 14px; border-bottom: 1px solid #eee; font-weight: bold; font-size: 14px; background: #fafafa; }
  .panel-body { padding: 14px; }

  label { display: block; font-size: 12px; color: #555; margin-bottom: 3px; margin-top: 8px; }
  input, select {
    width: 100%; padding: 7px 10px; border: 1px solid #ccc; border-radius: 4px;
    font-size: 13px; font-family: monospace; background: #fff;
  }
  input:focus, select:focus { outline: none; border-color: #0066cc; }

  .btn {
    display: inline-block; padding: 8px 16px; border: none; border-radius: 4px;
    font-size: 13px; cursor: pointer; margin-top: 10px;
  }
  .btn-primary { background: #0066cc; color: #fff; }
  .btn-primary:hover { background: #0055aa; }
  .btn-demo { background: #28a745; color: #fff; }
  .btn-demo:hover { background: #218838; }
  .btn-secondary { background: #eee; color: #333; border: 1px solid #ccc; }
  .btn-secondary:hover { background: #ddd; }

  .result { margin-top: 10px; padding: 10px; border-radius: 4px; font-size: 13px; font-family: monospace; word-break: break-all; line-height: 1.6; }
  .result.ok { background: #e6f9ee; border: 1px solid #b2dfdb; color: #2e7d32; }
  .result.err { background: #fdecea; border: 1px solid #f5c6cb; color: #c62828; }
  .result.info { background: #e3f2fd; border: 1px solid #bbdefb; color: #1565c0; }

  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { text-align: left; padding: 8px; background: #fafafa; border-bottom: 2px solid #ddd; font-size: 12px; color: #555; }
  td { padding: 8px; border-bottom: 1px solid #eee; font-family: monospace; font-size: 12px; }

  .tag { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 11px; font-weight: bold; }
  .tag-green { background: #e6f9ee; color: #2e7d32; }
  .tag-red { background: #fdecea; color: #c62828; }

  .block-card { background: #fafafa; border: 1px solid #e0e0e0; border-radius: 5px; padding: 12px; margin-bottom: 10px; }
  .block-idx { font-family: monospace; font-size: 13px; font-weight: bold; color: #0066cc; margin-bottom: 6px; }
  .block-row { display: flex; justify-content: space-between; font-size: 12px; color: #555; margin-bottom: 3px; }
  .block-row span:last-child { font-family: monospace; color: #333; text-align: right; max-width: 55%; overflow: hidden; text-overflow: ellipsis; }

  .shor-box { background: #fafafa; border: 1px solid #e0e0e0; border-radius: 5px; padding: 12px; margin-top: 10px; }
  .shor-row { display: flex; justify-content: space-between; font-size: 13px; padding: 4px 0; }
  .shor-row .label { color: #555; }
  .shor-row .val { font-family: monospace; font-weight: bold; }

  .demo-entry { display: flex; align-items: center; gap: 10px; padding: 6px 0; border-bottom: 1px solid #eee; font-size: 13px; }
  .demo-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
  .demo-step { font-weight: bold; min-width: 130px; color: #555; font-size: 12px; }

  .hidden { display: none; }
</style>
</head>
<body>

<div class="header">
  <div class="header-row">
    <div>
      <h1>EV Charging Payment Gateway</h1>
      <p>BITS F463 — Cryptography Term Project 2025-26</p>
    </div>
    <button class="btn btn-demo" onclick="runDemo()">Run Full Demo</button>
  </div>
</div>

<div class="tabs">
  <button class="tab active" onclick="switchTab(this,'tab-register')">Registration</button>
  <button class="tab" onclick="switchTab(this,'tab-kiosk')">Kiosk / QR</button>
  <button class="tab" onclick="switchTab(this,'tab-charge')">Charging Session</button>
  <button class="tab" onclick="switchTab(this,'tab-chain')">Blockchain</button>
  <button class="tab" onclick="switchTab(this,'tab-balances')">Balances</button>
  <button class="tab" onclick="switchTab(this,'tab-shor')">Shor's Attack</button>
  <button class="tab" onclick="switchTab(this,'tab-demo')">Demo Log</button>
</div>

<div class="content">

  <!-- REGISTRATION -->
  <div id="tab-register" class="tab-content">
    <div class="panel-grid">
      <div class="panel">
        <div class="panel-head">Register Franchise</div>
        <div class="panel-body">
          <label>Franchise Name</label>
          <input id="f_name" placeholder="e.g. Tata EV Hub">
          <label>Zone Code</label>
          <select id="f_zone"><option value="">Select zone...</option></select>
          <label>Password</label>
          <input id="f_pass" type="password">
          <label>Initial Balance</label>
          <input id="f_bal" type="number" value="10000">
          <button class="btn btn-primary" onclick="registerFranchise()">Register</button>
          <div id="f_result"></div>
        </div>
      </div>
      <div class="panel">
        <div class="panel-head">Register EV Owner</div>
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
          <button class="btn btn-primary" onclick="registerUser()">Register</button>
          <div id="u_result"></div>
        </div>
      </div>
    </div>
  </div>

  <!-- KIOSK -->
  <div id="tab-kiosk" class="tab-content hidden">
    <div class="panel-grid">
      <div class="panel">
        <div class="panel-head">Generate QR Code (ASCON Encryption)</div>
        <div class="panel-body">
          <label>Select Franchise</label>
          <select id="qr_fid"><option value="">Loading...</option></select>
          <button class="btn btn-primary" onclick="generateQR()">Encrypt FID & Generate QR</button>
          <div id="qr_result"></div>
        </div>
      </div>
      <div class="panel">
        <div class="panel-head">Active QR Sessions</div>
        <div class="panel-body" id="qr_sessions_list"><p style="color:#999">No QR sessions yet.</p></div>
      </div>
    </div>
  </div>

  <!-- CHARGING SESSION -->
  <div id="tab-charge" class="tab-content hidden">
    <div class="panel" style="max-width:480px;">
      <div class="panel-head">Initiate Charging Session</div>
      <div class="panel-body">
        <label>QR Session (Franchise)</label>
        <select id="ch_qr"><option value="">Select QR session...</option></select>
        <label>EV Owner</label>
        <select id="ch_user"><option value="">Select user...</option></select>
        <label>PIN</label>
        <input id="ch_pin" maxlength="4" placeholder="Enter PIN">
        <label>Amount (Rs.)</label>
        <input id="ch_amount" type="number" placeholder="500">
        <button class="btn btn-primary" onclick="chargeSession()">Process Payment</button>
        <div id="ch_result"></div>
      </div>
    </div>
  </div>

  <!-- BLOCKCHAIN -->
  <div id="tab-chain" class="tab-content hidden">
    <div style="margin-bottom:12px;">
      <button class="btn btn-primary" onclick="loadBlockchain()">Refresh</button>
      <button class="btn btn-secondary" onclick="validateChain()">Validate Integrity</button>
    </div>
    <div id="chain_valid"></div>
    <div id="chain_list"></div>
  </div>

  <!-- BALANCES -->
  <div id="tab-balances" class="tab-content hidden">
    <button class="btn btn-primary" onclick="loadBalances()" style="margin-bottom:12px;">Refresh</button>
    <div class="panel-grid">
      <div class="panel">
        <div class="panel-head">Franchises</div>
        <div class="panel-body"><table><thead><tr><th>Name</th><th>Zone</th><th>Balance</th><th>Status</th></tr></thead><tbody id="bal_franchises"></tbody></table></div>
      </div>
      <div class="panel">
        <div class="panel-head">EV Owners</div>
        <div class="panel-body"><table><thead><tr><th>Name</th><th>VMID</th><th>Balance</th><th>Status</th></tr></thead><tbody id="bal_users"></tbody></table></div>
      </div>
    </div>
  </div>

  <!-- SHOR -->
  <div id="tab-shor" class="tab-content hidden">
    <div class="panel" style="max-width:520px;">
      <div class="panel-head">Shor's Algorithm - Quantum Attack Demo</div>
      <div class="panel-body">
        <p style="font-size:13px;color:#666;margin-bottom:12px;">
          Simulates Shor's algorithm to factor the RSA modulus and recover the private key.
        </p>
        <button class="btn btn-primary" onclick="runShor()">Run Shor's Algorithm</button>
        <div id="shor_result"></div>
      </div>
    </div>
  </div>

  <!-- DEMO LOG -->
  <div id="tab-demo" class="tab-content hidden">
    <div class="panel">
      <div class="panel-head">Full Demo Log</div>
      <div class="panel-body" id="demo_log" style="max-height:400px;overflow-y:auto;">
        <p style="color:#999">Click "Run Full Demo" to execute the automated demonstration.</p>
      </div>
    </div>
  </div>

</div>

<script>
async function api(url, opts) { const r = await fetch(url, opts); return r.json(); }
function post(url, data) { return api(url, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)}); }
function $(id) { return document.getElementById(id); }
function showResult(el, data) {
  const d = $(el);
  if (data.success) {
    d.className = 'result ok';
    d.innerHTML = Object.entries(data).filter(([k])=>k!=='success').map(([k,v])=>`<b>${k}:</b> ${v}`).join('<br>');
  } else {
    d.className = 'result err';
    d.innerHTML = data.error || 'Failed';
  }
}

function switchTab(btn, id) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(t => t.classList.add('hidden'));
  btn.classList.add('active');
  $(id).classList.remove('hidden');
  if (id === 'tab-kiosk') { loadFranchiseSelect(); loadQRSessions(); }
  if (id === 'tab-charge') { loadChargeSelects(); }
  if (id === 'tab-chain') { loadBlockchain(); }
  if (id === 'tab-balances') { loadBalances(); }
}

async function loadZones() {
  const providers = await api('/api/providers');
  ['f_zone','u_zone'].forEach(sel => {
    const s = $(sel);
    s.innerHTML = '<option value="">Select zone...</option>';
    for (const [prov, zones] of Object.entries(providers)) {
      zones.forEach(z => { s.innerHTML += `<option value="${z}">${z} (${prov})</option>`; });
    }
  });
}

async function registerFranchise() {
  const data = await post('/api/register_franchise', {
    name: $('f_name').value, zone_code: $('f_zone').value,
    password: $('f_pass').value, balance: $('f_bal').value
  });
  showResult('f_result', data);
}
async function registerUser() {
  const data = await post('/api/register_user', {
    name: $('u_name').value, zone_code: $('u_zone').value,
    password: $('u_pass').value, pin: $('u_pin').value,
    mobile: $('u_mobile').value, balance: $('u_bal').value
  });
  showResult('u_result', data);
}

async function loadFranchiseSelect() {
  const items = await api('/api/franchises');
  const s = $('qr_fid');
  s.innerHTML = '<option value="">Select franchise...</option>';
  items.forEach(f => { s.innerHTML += `<option value="${f.fid}">${f.name} (${f.zone_code})</option>`; });
}
async function generateQR() {
  const data = await post('/api/generate_qr', {fid: $('qr_fid').value});
  if (data.success) {
    $('qr_result').className = 'result ok';
    $('qr_result').innerHTML = `QR generated for <b>${data.franchise_name}</b><br>Session: ${data.session_id.slice(0,16)}...<br>VFID (encrypted): ${data.vfid}`;
  } else { showResult('qr_result', data); }
  loadQRSessions();
}
async function loadQRSessions() {
  const items = await api('/api/qr_sessions');
  const el = $('qr_sessions_list');
  if (!items.length) { el.innerHTML = '<p style="color:#999">No QR sessions yet.</p>'; return; }
  let html = '<table><thead><tr><th>Franchise</th><th>Session ID</th><th>VFID</th></tr></thead><tbody>';
  items.forEach(s => { html += `<tr><td>${s.franchise_name}</td><td>${s.session_id.slice(0,12)}...</td><td>${s.vfid.slice(0,12)}...</td></tr>`; });
  el.innerHTML = html + '</tbody></table>';
}

async function loadChargeSelects() {
  const sessions = await api('/api/qr_sessions');
  const s1 = $('ch_qr');
  s1.innerHTML = '<option value="">Select QR session...</option>';
  sessions.forEach(s => { s1.innerHTML += `<option value='${s.qr_data}'>${s.franchise_name} (${s.session_id.slice(0,10)}...)</option>`; });
  const users = await api('/api/users');
  const s2 = $('ch_user');
  s2.innerHTML = '<option value="">Select user...</option>';
  users.forEach(u => { s2.innerHTML += `<option value="${u.vmid}">${u.name} - Rs.${u.balance.toFixed(0)}</option>`; });
}
async function chargeSession() {
  const data = await post('/api/charge', {
    qr_data: $('ch_qr').value, vmid: $('ch_user').value,
    pin: $('ch_pin').value, amount: $('ch_amount').value
  });
  const el = $('ch_result');
  if (data.success) {
    el.className = 'result ok';
    el.innerHTML = `Payment approved! Block #${data.block_index} | Txn: ${data.transaction_id?.slice(0,24)}...<br>User balance: Rs.${data.user_balance?.toFixed(2)} | Franchise balance: Rs.${data.franchise_balance?.toFixed(2)}`;
  } else if (data.refund) {
    el.className = 'result err';
    el.innerHTML = `Hardware failure! Refund issued. Balance restored: Rs.${data.user_balance?.toFixed(2)}`;
  } else { showResult('ch_result', data); }
}

async function loadBlockchain() {
  const blocks = await api('/api/blockchain');
  const el = $('chain_list');
  let html = '';
  blocks.forEach(b => {
    const dispute = b.dispute ? ' <span class="tag tag-red">DISPUTE/REFUND</span>' : '';
    html += `<div class="block-card">
      <div class="block-idx">Block #${b.index}${dispute}</div>
      <div class="block-row"><span>Txn ID</span><span>${b.transaction_id.slice(0,32)}...</span></div>
      <div class="block-row"><span>Time</span><span>${b.timestamp}</span></div>
      <div class="block-row"><span>Amount</span><span>Rs.${b.amount.toFixed(2)}</span></div>
      <div class="block-row"><span>Description</span><span>${b.description || '-'}</span></div>
      <div class="block-row"><span>Prev Hash</span><span>${b.prev_hash.slice(0,24)}...</span></div>
      <div class="block-row"><span>Block Hash</span><span>${b.hash.slice(0,24)}...</span></div>
    </div>`;
  });
  el.innerHTML = html || '<p style="color:#999">No blocks yet.</p>';
}
async function validateChain() {
  const data = await api('/api/validate_chain');
  const el = $('chain_valid');
  el.className = data.valid ? 'result ok' : 'result err';
  el.innerHTML = data.message;
}

async function loadBalances() {
  const franchises = await api('/api/franchises');
  const users = await api('/api/users');
  $('bal_franchises').innerHTML = franchises.length ?
    franchises.map(f => `<tr><td>${f.name}</td><td>${f.zone_code}</td><td>Rs.${f.balance.toFixed(2)}</td><td><span class="tag ${f.active?'tag-green':'tag-red'}">${f.active?'Active':'Inactive'}</span></td></tr>`).join('') :
    '<tr><td colspan="4" style="color:#999">None registered</td></tr>';
  $('bal_users').innerHTML = users.length ?
    users.map(u => `<tr><td>${u.name}</td><td>${u.vmid}</td><td>Rs.${u.balance.toFixed(2)}</td><td><span class="tag ${u.active?'tag-green':'tag-red'}">${u.active?'Active':'Inactive'}</span></td></tr>`).join('') :
    '<tr><td colspan="4" style="color:#999">None registered</td></tr>';
}

async function runShor() {
  $('shor_result').innerHTML = '<div class="result info">Running Shor\'s algorithm...</div>';
  const d = await api('/api/shor');
  let html = '<div class="shor-box">';
  html += `<div class="shor-row"><span class="label">RSA Public Key (e)</span><span class="val">${d.e}</span></div>`;
  html += `<div class="shor-row"><span class="label">RSA Modulus (n)</span><span class="val">${d.n}</span></div>`;
  html += `<div class="shor-row"><span class="label">Actual primes</span><span class="val">p=${d.real_p}, q=${d.real_q}</span></div>`;
  html += '<hr style="margin:6px 0;border-color:#ddd">';
  html += `<div class="shor-row"><span class="label">Factors found</span><span class="val" style="color:#2e7d32">${d.p_found}, ${d.q_found}</span></div>`;
  html += `<div class="shor-row"><span class="label">Private key (d) original</span><span class="val">${d.d_original}</span></div>`;
  html += `<div class="shor-row"><span class="label">Private key (d) recovered</span><span class="val" style="color:${d.match?'#2e7d32':'#c62828'}">${d.d_recovered ?? 'FAILED'}</span></div>`;
  html += `<div class="shor-row"><span class="label">Keys match?</span><span class="val" style="color:${d.match?'#2e7d32':'#c62828'}">${d.match?'YES':'NO'}</span></div>`;
  html += `<div class="shor-row"><span class="label">Time</span><span class="val">${d.elapsed}s</span></div>`;
  html += '</div>';
  if (d.key_recovered) {
    html += '<div class="result err" style="margin-top:10px;">RSA broken! Private key recovered via quantum factoring. Post-quantum algorithms are needed.</div>';
  }
  $('shor_result').innerHTML = html;
}

async function runDemo() {
  document.querySelectorAll('.tab')[6].click();
  $('demo_log').innerHTML = '<p style="color:#0066cc">Running full demo...</p>';
  const data = await post('/api/run_demo', {});
  let html = '';
  (data.log || []).forEach(entry => {
    const color = entry.success ? '#2e7d32' : '#c62828';
    html += `<div class="demo-entry">
      <div class="demo-dot" style="background:${color}"></div>
      <div class="demo-step">${entry.step}</div>
      <div>${entry.detail}</div>
    </div>`;
  });
  $('demo_log').innerHTML = html || '<p>No results.</p>';
}

loadZones();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("  EV CHARGING GATEWAY — Web UI")
    print("  Open http://localhost:5000 in your browser")
    print("=" * 55 + "\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
