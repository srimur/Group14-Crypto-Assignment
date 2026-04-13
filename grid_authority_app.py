import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template_string, request, jsonify
from entities.grid_authority import GridAuthority
from crypto_utils.shor_simulation import shor_factor
from config import ENERGY_PROVIDERS

app = Flask(__name__)
grid = GridAuthority()


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/providers")
def api_providers():
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

    from entities.franchise import Franchise
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

    from entities.ev_owner import EVOwner
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


# Called by the Kiosk after it decrypts the QR code
@app.route("/api/process_transaction", methods=["POST"])
def api_process_transaction():
    data = request.json
    fid = data.get("fid", "").strip()
    vmid = data.get("vmid", "").strip()
    pin = data.get("pin", "").strip()
    amount = float(data.get("amount", 0))

    if not all([fid, vmid, pin]) or amount <= 0:
        return jsonify({"success": False, "error": "All fields are required."})

    result = grid.process_transaction(fid=fid, vmid=vmid, pin=pin, amount=amount)
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


# ──────────────────────────────────────────────
# HTML TEMPLATE
# ──────────────────────────────────────────────

HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Grid Authority - EV Charging Gateway</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:Arial,sans-serif; background:#f5f5f5; color:#333; font-size:14px; }
  .header { background:#0d47a1; color:#fff; padding:14px 20px; }
  .header h1 { font-size:18px; }
  .header p { font-size:12px; opacity:0.8; }
  .tabs { display:flex; background:#fff; border-bottom:1px solid #ddd; flex-wrap:wrap; }
  .tab { padding:10px 16px; font-size:13px; cursor:pointer; border:none; background:none; color:#555; border-bottom:2px solid transparent; }
  .tab:hover { color:#000; }
  .tab.active { color:#0d47a1; border-bottom-color:#0d47a1; font-weight:bold; }
  .content { padding:20px; max-width:1100px; margin:0 auto; }
  .panel-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:16px; }
  .panel { background:#fff; border:1px solid #ddd; border-radius:6px; }
  .panel-head { padding:10px 14px; border-bottom:1px solid #eee; font-weight:bold; font-size:14px; background:#e3f2fd; color:#0d47a1; }
  .panel-body { padding:14px; }
  label { display:block; font-size:12px; color:#555; margin-bottom:3px; margin-top:8px; }
  input,select { width:100%; padding:7px 10px; border:1px solid #ccc; border-radius:4px; font-size:13px; font-family:monospace; }
  input:focus,select:focus { outline:none; border-color:#0d47a1; }
  .btn { display:inline-block; padding:8px 16px; border:none; border-radius:4px; font-size:13px; cursor:pointer; margin-top:10px; }
  .btn-primary { background:#0d47a1; color:#fff; }
  .btn-primary:hover { background:#1565c0; }
  .btn-secondary { background:#eee; color:#333; border:1px solid #ccc; }
  .result { margin-top:10px; padding:10px; border-radius:4px; font-size:13px; font-family:monospace; word-break:break-all; line-height:1.6; }
  .result.ok { background:#e6f9ee; border:1px solid #b2dfdb; color:#2e7d32; }
  .result.err { background:#fdecea; border:1px solid #f5c6cb; color:#c62828; }
  .result.info { background:#e3f2fd; border:1px solid #bbdefb; color:#1565c0; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th { text-align:left; padding:8px; background:#e3f2fd; border-bottom:2px solid #ddd; font-size:12px; color:#0d47a1; }
  td { padding:8px; border-bottom:1px solid #eee; font-family:monospace; font-size:12px; }
  .tag { display:inline-block; padding:2px 8px; border-radius:3px; font-size:11px; font-weight:bold; }
  .tag-green { background:#e6f9ee; color:#2e7d32; }
  .tag-red { background:#fdecea; color:#c62828; }
  .block-card { background:#fafafa; border:1px solid #e0e0e0; border-radius:5px; padding:12px; margin-bottom:10px; }
  .block-idx { font-family:monospace; font-size:13px; font-weight:bold; color:#0d47a1; margin-bottom:6px; }
  .block-row { display:flex; justify-content:space-between; font-size:12px; color:#555; margin-bottom:3px; }
  .block-row span:last-child { font-family:monospace; color:#333; text-align:right; max-width:55%; overflow:hidden; text-overflow:ellipsis; }
  .shor-box { background:#fafafa; border:1px solid #e0e0e0; border-radius:5px; padding:12px; margin-top:10px; }
  .shor-row { display:flex; justify-content:space-between; font-size:13px; padding:4px 0; }
  .shor-row .label { color:#555; } .shor-row .val { font-family:monospace; font-weight:bold; }
  .hidden { display:none; }
</style>
</head>
<body>

<div class="header">
  <h1>Grid Authority Laptop</h1>
  <p>Central governing body — Registers entities, maintains blockchain, manages balances</p>
</div>

<div class="tabs">
  <button class="tab active" onclick="switchTab(this,'tab-register')">Register Franchise</button>
  <button class="tab" onclick="switchTab(this,'tab-entities')">Registered Entities</button>
  <button class="tab" onclick="switchTab(this,'tab-chain')">Blockchain</button>
  <button class="tab" onclick="switchTab(this,'tab-balances')">Balances</button>
  <button class="tab" onclick="switchTab(this,'tab-shor')">Shor's Attack</button>
</div>

<div class="content">

  <!-- REGISTER FRANCHISE -->
  <div id="tab-register" class="tab-content">
    <div class="panel" style="max-width:480px;">
      <div class="panel-head">Register New Franchise</div>
      <div class="panel-body">
        <label>Franchise Name</label>
        <input id="f_name" placeholder="e.g. Tata EV Hub">
        <label>Zone Code</label>
        <select id="f_zone"><option value="">Select zone...</option></select>
        <label>Password</label>
        <input id="f_pass" type="password">
        <label>Initial Balance</label>
        <input id="f_bal" type="number" value="10000">
        <button class="btn btn-primary" onclick="registerFranchise()">Register Franchise</button>
        <div id="f_result"></div>
      </div>
    </div>
  </div>

  <!-- ENTITIES -->
  <div id="tab-entities" class="tab-content hidden">
    <div class="panel-grid">
      <div class="panel">
        <div class="panel-head">Franchises</div>
        <div class="panel-body"><table><thead><tr><th>Name</th><th>Zone</th><th>FID</th><th>Status</th></tr></thead><tbody id="tbl_franchises"></tbody></table></div>
      </div>
      <div class="panel">
        <div class="panel-head">EV Owners</div>
        <div class="panel-body"><table><thead><tr><th>Name</th><th>VMID</th><th>Zone</th><th>Status</th></tr></thead><tbody id="tbl_users"></tbody></table></div>
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
        <div class="panel-head">Franchise Balances</div>
        <div class="panel-body"><table><thead><tr><th>Name</th><th>Zone</th><th>Balance</th></tr></thead><tbody id="bal_f"></tbody></table></div>
      </div>
      <div class="panel">
        <div class="panel-head">User Balances</div>
        <div class="panel-body"><table><thead><tr><th>Name</th><th>VMID</th><th>Balance</th></tr></thead><tbody id="bal_u"></tbody></table></div>
      </div>
    </div>
  </div>

  <!-- SHOR -->
  <div id="tab-shor" class="tab-content hidden">
    <div class="panel" style="max-width:520px;">
      <div class="panel-head">Shor's Algorithm — Quantum Attack Demo</div>
      <div class="panel-body">
        <p style="font-size:13px;color:#666;margin-bottom:12px;">Factor the RSA modulus and recover the private key.</p>
        <button class="btn btn-primary" onclick="runShor()">Run Shor's Algorithm</button>
        <div id="shor_result"></div>
      </div>
    </div>
  </div>

</div>

<script>
async function api(url,opts){const r=await fetch(url,opts);return r.json();}
function post(url,data){return api(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});}
function $(id){return document.getElementById(id);}

function switchTab(btn,id){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(t=>t.classList.add('hidden'));
  btn.classList.add('active'); $(id).classList.remove('hidden');
  if(id==='tab-entities') loadEntities();
  if(id==='tab-chain') loadBlockchain();
  if(id==='tab-balances') loadBalances();
}

async function loadZones(){
  const providers=await api('/api/providers');
  const s=$('f_zone');
  s.innerHTML='<option value="">Select zone...</option>';
  for(const[prov,zones] of Object.entries(providers)){
    zones.forEach(z=>{s.innerHTML+=`<option value="${z}">${z} (${prov})</option>`;});
  }
}

async function registerFranchise(){
  const data=await post('/api/register_franchise',{
    name:$('f_name').value, zone_code:$('f_zone').value,
    password:$('f_pass').value, balance:$('f_bal').value
  });
  const el=$('f_result');
  if(data.success){el.className='result ok';el.innerHTML=`Registered! FID: ${data.fid}<br>Provider: ${data.provider}`;}
  else{el.className='result err';el.innerHTML=data.error;}
}

async function loadEntities(){
  const franchises=await api('/api/franchises');
  const users=await api('/api/users');
  $('tbl_franchises').innerHTML=franchises.length?
    franchises.map(f=>`<tr><td>${f.name}</td><td>${f.zone_code}</td><td style="font-size:11px">${f.fid}</td><td><span class="tag ${f.active?'tag-green':'tag-red'}">${f.active?'Active':'Inactive'}</span></td></tr>`).join(''):'<tr><td colspan="4" style="color:#999">None</td></tr>';
  $('tbl_users').innerHTML=users.length?
    users.map(u=>`<tr><td>${u.name}</td><td style="font-size:11px">${u.vmid}</td><td>${u.zone_code}</td><td><span class="tag ${u.active?'tag-green':'tag-red'}">${u.active?'Active':'Inactive'}</span></td></tr>`).join(''):'<tr><td colspan="4" style="color:#999">None</td></tr>';
}

async function loadBlockchain(){
  const blocks=await api('/api/blockchain');
  let html='';
  blocks.forEach(b=>{
    const dispute=b.dispute?' <span class="tag tag-red">DISPUTE/REFUND</span>':'';
    html+=`<div class="block-card">
      <div class="block-idx">Block #${b.index}${dispute}</div>
      <div class="block-row"><span>Txn ID</span><span>${b.transaction_id.slice(0,32)}...</span></div>
      <div class="block-row"><span>Time</span><span>${b.timestamp}</span></div>
      <div class="block-row"><span>Amount</span><span>Rs.${b.amount.toFixed(2)}</span></div>
      <div class="block-row"><span>Description</span><span>${b.description||'-'}</span></div>
      <div class="block-row"><span>Prev Hash</span><span>${b.prev_hash.slice(0,24)}...</span></div>
      <div class="block-row"><span>Block Hash</span><span>${b.hash.slice(0,24)}...</span></div>
    </div>`;
  });
  $('chain_list').innerHTML=html||'<p style="color:#999">No blocks yet.</p>';
}

async function validateChain(){
  const data=await api('/api/validate_chain');
  const el=$('chain_valid');
  el.className=data.valid?'result ok':'result err';
  el.innerHTML=data.message;
}

async function loadBalances(){
  const franchises=await api('/api/franchises');
  const users=await api('/api/users');
  $('bal_f').innerHTML=franchises.length?
    franchises.map(f=>`<tr><td>${f.name}</td><td>${f.zone_code}</td><td>Rs.${f.balance.toFixed(2)}</td></tr>`).join(''):'<tr><td colspan="3" style="color:#999">None</td></tr>';
  $('bal_u').innerHTML=users.length?
    users.map(u=>`<tr><td>${u.name}</td><td>${u.vmid}</td><td>Rs.${u.balance.toFixed(2)}</td></tr>`).join(''):'<tr><td colspan="3" style="color:#999">None</td></tr>';
}

async function runShor(){
  $('shor_result').innerHTML='<div class="result info">Running Shor\'s algorithm...</div>';
  const d=await api('/api/shor');
  let html='<div class="shor-box">';
  html+=`<div class="shor-row"><span class="label">RSA Public Key (e)</span><span class="val">${d.e}</span></div>`;
  html+=`<div class="shor-row"><span class="label">RSA Modulus (n)</span><span class="val">${d.n}</span></div>`;
  html+=`<div class="shor-row"><span class="label">Actual primes</span><span class="val">p=${d.real_p}, q=${d.real_q}</span></div>`;
  html+='<hr style="margin:6px 0;border-color:#ddd">';
  html+=`<div class="shor-row"><span class="label">Factors found</span><span class="val" style="color:#2e7d32">${d.p_found}, ${d.q_found}</span></div>`;
  html+=`<div class="shor-row"><span class="label">Private key (d) original</span><span class="val">${d.d_original}</span></div>`;
  html+=`<div class="shor-row"><span class="label">Private key (d) recovered</span><span class="val" style="color:${d.match?'#2e7d32':'#c62828'}">${d.d_recovered??'FAILED'}</span></div>`;
  html+=`<div class="shor-row"><span class="label">Keys match?</span><span class="val" style="color:${d.match?'#2e7d32':'#c62828'}">${d.match?'YES':'NO'}</span></div>`;
  html+=`<div class="shor-row"><span class="label">Time</span><span class="val">${d.elapsed}s</span></div>`;
  html+='</div>';
  if(d.key_recovered){html+='<div class="result err" style="margin-top:10px;">RSA broken! Private key recovered via quantum factoring.</div>';}
  $('shor_result').innerHTML=html;
}

loadZones();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("  GRID AUTHORITY LAPTOP — Port 5000")
    print("  http://localhost:5000")
    print("=" * 55 + "\n")
    app.run(debug=True, host="127.0.0.1", port=5000)
