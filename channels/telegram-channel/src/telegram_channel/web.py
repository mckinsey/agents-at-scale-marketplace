import json
import logging
import threading
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

from .k8s import K8sClient
from .state import ConversationState

logger = logging.getLogger("telegram-channel")

_ctx: dict = {}

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  background:#141721;color:#ffffffe0;min-height:100vh}
.container{max-width:600px;margin:0 auto;padding:32px 20px}
h1{font-size:18px;font-weight:600;letter-spacing:-0.01em}
.subtitle{color:#ffffff99;font-size:13px;margin-top:2px;margin-bottom:28px}
.card{background:#232632;border:1px solid #ffffff1a;border-radius:8px;padding:20px;margin-bottom:12px}
.card h2{font-size:12px;font-weight:500;color:#ffffff99;text-transform:uppercase;
  letter-spacing:0.06em;margin-bottom:14px}
.bot-header{display:flex;align-items:center;gap:10px;margin-bottom:16px}
.dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.dot.ok{background:#40d86e}
.dot.err{background:#f56565}
.dot.warn{background:#ffc107}
.bot-name{font-size:16px;font-weight:600}
.bot-link{color:#ffffff99;font-size:12px}
.bot-link a{color:#00b4ff;text-decoration:none}
.bot-link a:hover{text-decoration:underline}
.qr{display:flex;align-items:center;gap:20px;flex-wrap:wrap}
.qr-img{background:#fff;padding:10px;border-radius:6px;flex-shrink:0}
.qr-img img{display:block;width:140px;height:140px}
.qr-text p{color:#ffffff99;font-size:13px;line-height:1.5}
.qr-text .scan{color:#ffffffe0;font-weight:500;font-size:14px;margin-bottom:4px}
.agent-list{list-style:none}
.agent-list li{display:flex;justify-content:space-between;align-items:center;
  padding:8px 0;border-bottom:1px solid #ffffff1a}
.agent-list li:last-child{border-bottom:none}
.agent-name{font-weight:500;font-size:14px}
.agent-desc{color:#ffffff61;font-size:12px;text-align:right;max-width:50%}
.stat-row{display:flex;justify-content:space-between;padding:6px 0}
.stat-label{color:#ffffff99;font-size:13px}
.stat-value{font-weight:500;font-size:13px}
.empty{color:#ffffff61;font-style:italic;font-size:13px}
.setup-step{display:flex;gap:12px;margin-bottom:16px}
.step-num{background:#2b2e39;border:1px solid #ffffff1a;width:28px;height:28px;
  border-radius:50%;display:flex;align-items:center;justify-content:center;
  font-size:12px;font-weight:600;flex-shrink:0;color:#00b4ff}
.step-content{flex:1}
.step-content h3{font-size:14px;font-weight:500;margin-bottom:4px}
.step-content p{color:#ffffff99;font-size:13px;line-height:1.5}
.step-content code{background:#2b2e39;padding:2px 6px;border-radius:3px;font-size:12px;
  font-family:'SF Mono',Menlo,monospace;color:#00b4ff}
label{display:block;font-size:13px;font-weight:500;margin-bottom:6px;color:#ffffff99}
input[type=text]{width:100%;background:#2b2e39;border:1px solid #ffffff1a;
  border-radius:6px;padding:10px 12px;color:#ffffffe0;font-size:14px;
  font-family:inherit;outline:none;transition:border-color 0.15s}
input[type=text]:focus{border-color:#00b4ff}
input[type=text]::placeholder{color:#ffffff61}
.field{margin-bottom:14px}
.btn{background:#00b4ff;color:#fff;border:none;border-radius:6px;padding:10px 20px;
  font-size:14px;font-weight:500;cursor:pointer;font-family:inherit;transition:background 0.15s}
.btn:hover{background:#009ee0}
.btn:disabled{opacity:0.5;cursor:not-allowed}
.btn-row{margin-top:8px}
.msg{padding:12px;border-radius:6px;font-size:13px;margin-bottom:12px}
.msg.ok{background:#40d86e22;border:1px solid #40d86e44;color:#40d86e}
.msg.err{background:#f5656522;border:1px solid #f5656544;color:#f56565}
.docs-link{margin-top:16px;font-size:13px;color:#ffffff99}
.docs-link a{color:#00b4ff;text-decoration:none}
.err-box{background:#f5656522;border:1px solid #f5656544;border-radius:6px;
  padding:12px;font-size:13px;color:#f56565;margin-bottom:16px}
"""


def start_web_server(
    port: int,
    k8s: K8sClient,
    state: ConversationState,
    secret_name: str,
    configured: threading.Event,
):
    _ctx["k8s"] = k8s
    _ctx["state"] = state
    _ctx["secret_name"] = secret_name
    _ctx["configured"] = configured
    server = HTTPServer(("0.0.0.0", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Web UI listening on :{port}")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"status": "ok"})
        elif self.path in ("/", "/ui"):
            self._html(200, _render_page())
        elif self.path == "/api/status":
            self._json(200, _get_status())
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode()
        content_type = self.headers.get("Content-Type", "")
        if "json" in content_type:
            data = json.loads(body)
        else:
            data = {k: v[0] for k, v in parse_qs(body).items()}

        if self.path == "/api/test":
            result = _handle_test(data)
            self._json(result["code"], result)
        elif self.path == "/api/configure":
            result = _handle_configure(data)
            self._json(result["code"], result)
        else:
            self._json(404, {"error": "not found"})

    def _json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, code, html):
        body = html.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


def _handle_test(data: dict) -> dict:
    token = data.get("token", "").strip()
    bridge_url = data.get("bridge_url", "").strip()
    if not token:
        return {"code": 400, "error": "Bot token is required"}

    base = bridge_url if bridge_url else "https://api.telegram.org/bot"
    url = f"{base}{token}/getMe"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            bot = result["result"]
            return {
                "code": 200,
                "bot": {
                    "username": bot.get("username", ""),
                    "first_name": bot.get("first_name", ""),
                },
            }
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return {"code": 401, "error": "Invalid bot token"}
        return {"code": e.code, "error": f"Telegram API returned HTTP {e.code}"}
    except urllib.error.URLError as e:
        return {
            "code": 502,
            "error": f"Cannot reach Telegram API ({e.reason}). You may need to set a Telegram API URL.",
        }


def _handle_configure(data: dict) -> dict:
    token = data.get("token", "").strip()
    bridge_url = data.get("bridge_url", "").strip()
    if not token:
        return {"code": 400, "error": "Bot token is required"}

    k8s: K8sClient = _ctx["k8s"]
    secret_name = _ctx["secret_name"]
    secret_data = {"token": token}
    if bridge_url:
        secret_data["bridge-url"] = bridge_url

    k8s.save_secret(secret_name, secret_data)
    _ctx["configured"].set()

    return {"code": 200, "message": "Configuration saved."}


def _get_status() -> dict:
    bot = _ctx.get("bot_info")
    k8s: K8sClient = _ctx.get("k8s")
    state: ConversationState = _ctx.get("state")

    agents = []
    try:
        if k8s:
            agents = k8s.list_agents()
    except Exception as e:
        logger.warning(f"Failed to list agents for status: {e}")

    secret_name = _ctx.get("secret_name", "telegram-bot-token")
    secret_exists = False
    try:
        if k8s:
            secret_exists = k8s.get_secret(secret_name) is not None
    except Exception:
        pass

    return {
        "configured": bot is not None,
        "error": _ctx.get("error"),
        "secret": {
            "name": secret_name,
            "namespace": k8s.namespace if k8s else "default",
            "exists": secret_exists,
        },
        "bot": {
            "username": bot.get("username", ""),
            "first_name": bot.get("first_name", ""),
            "link": f"https://t.me/{bot.get('username', '')}",
        } if bot else None,
        "agents": agents,
        "conversations": len(state._sessions) if state else 0,
    }


def _render_page() -> str:
    bot = _ctx.get("bot_info")
    if bot:
        return _render_connected(bot)
    return _render_setup()


def _render_setup() -> str:
    error = _ctx.get("error", "")
    base_url = _ctx.get("base_url", "")
    has_bridge = "api.telegram.org" not in base_url

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Telegram Channel — Setup</title>
<style>{CSS}</style>
</head><body>
<div class="container">
<h1>Ark — Telegram Channel</h1>
<p class="subtitle">Connect Ark agents to Telegram</p>

{f'<div class="err-box">{error}</div>' if error and error != "No bot token configured." else ""}

<div class="card">
<h2>Setup</h2>

<div class="setup-step">
 <div class="step-num">1</div>
 <div class="step-content">
  <h3>Get a bot token</h3>
  <p>If you already have a Telegram bot, grab its token. Otherwise, open Telegram and message
  <a href="https://t.me/BotFather" style="color:#00b4ff">@BotFather</a> — send <code>/newbot</code>
  and follow the prompts.</p>
 </div>
</div>

<div class="setup-step">
 <div class="step-num">2</div>
 <div class="step-content">
  <h3>Configure</h3>
  <p>Paste the bot token and test the connection.</p>
 </div>
</div>

<div id="result"></div>

<form id="config-form" onsubmit="return submitForm(event)">
 <div class="field">
  <label for="token">Bot Token *</label>
  <input type="text" id="token" name="token" placeholder="123456789:ABCdefGhi..." required>
 </div>
 <div class="field">
  <label for="bridge_url">Telegram API URL <span style="color:#ffffff61">(optional)</span></label>
  <input type="text" id="bridge_url" name="bridge_url"
   placeholder="https://api.telegram.org/bot"
   value="{base_url if has_bridge else ''}">
  <p style="color:#ffffff61;font-size:12px;margin-top:4px">
   Defaults to <code>https://api.telegram.org/bot</code>. Only change this if you
   cannot access the Telegram APIs directly (e.g. your network requires a bridge API URL — paste it here).
  </p>
 </div>
 <div class="btn-row" style="display:flex;gap:8px">
  <button type="button" class="btn" id="test-btn" onclick="testConnection()"
   style="background:#2b2e39;border:1px solid #ffffff1a">Test Connection</button>
  <button type="submit" class="btn" id="submit-btn">Save &amp; Connect</button>
 </div>
</form>

<div id="secret-info" style="font-size:12px;color:#ffffff61;margin-top:16px"></div>

<div class="docs-link">
 Telegram Channel v0.1.0 &middot;
 <a href="https://github.com/mckinsey/agents-at-scale-marketplace" target="_blank">Open Documentation</a>
</div>
</div>
</div>

<script>
fetch('/api/status').then(r=>r.json()).then(d=>{{
 if(d.secret){{
  var s=d.secret;
  var el=document.getElementById('secret-info');
  var state=s.exists?'<span style="color:#40d86e">configured</span>':'<span style="color:#ffffff61">not found</span>';
  el.innerHTML='Credentials stored in <code>Secret</code> <code>'+s.namespace+'/'+s.name+'</code> \u2014 '+state;
 }}
}}).catch(function(){{}});
function getFormData(){{
 return {{
  token:document.getElementById('token').value,
  bridge_url:document.getElementById('bridge_url').value
 }};
}}
function testConnection(){{
 var btn=document.getElementById('test-btn');
 var res=document.getElementById('result');
 if(!document.getElementById('token').value){{
  res.innerHTML='<div class="msg err">Enter a bot token first</div>';return;
 }}
 btn.disabled=true;btn.textContent='Testing...';
 fetch('/api/test',{{
  method:'POST',
  headers:{{'Content-Type':'application/json'}},
  body:JSON.stringify(getFormData())
 }}).then(r=>r.json()).then(d=>{{
  if(d.code===200){{
   res.innerHTML='<div class="msg ok">Connected to @'+d.bot.username+' ('+d.bot.first_name+')</div>';
  }}else{{
   res.innerHTML='<div class="msg err">'+(d.error||'Connection failed')+'</div>';
  }}
  btn.disabled=false;btn.textContent='Test Connection';
 }}).catch(()=>{{
  res.innerHTML='<div class="msg err">Request failed</div>';
  btn.disabled=false;btn.textContent='Test Connection';
 }});
}}
function showConnected(bot){{
 var link='https://t.me/'+bot.username;
 var qr='https://api.qrserver.com/v1/create-qr-code/?size=200x200&data='+encodeURIComponent(link);
 document.querySelector('.container').innerHTML=
  '<h1>Ark \u2014 Telegram Channel</h1>'+
  '<p class="subtitle">Ark agent gateway via Telegram</p>'+
  '<div class="card">'+
   '<div class="bot-header">'+
    '<span class="dot ok"></span>'+
    '<div><div class="bot-name">@'+bot.username+'</div>'+
    '<div class="bot-link"><a href="'+link+'" target="_blank">'+link+'</a></div></div>'+
   '</div>'+
   '<div class="qr">'+
    '<div class="qr-img"><a href="'+link+'" target="_blank">'+
     '<img src="'+qr+'" alt="QR"></a></div>'+
    '<div class="qr-text"><p class="scan">Scan to chat</p>'+
     '<p>Open Telegram and scan this code, or tap the link. Send /start to pick an agent.</p>'+
    '</div>'+
   '</div>'+
  '</div>'+
  '<div class="card"><h2>Agents</h2><div id="agents-list"><span class="empty">Loading...</span></div></div>'+
  '<div class="card"><h2>Status</h2>'+
   '<div class="stat-row"><span class="stat-label">Active conversations</span>'+
   '<span class="stat-value" id="conv-count">&mdash;</span></div></div>'+
  '<div class="docs-link" style="margin-top:8px">Telegram Channel v0.1.0 &middot; '+
   '<a href="https://github.com/mckinsey/agents-at-scale-marketplace" target="_blank">Open Documentation</a></div>';
 fetch('/api/status').then(r=>r.json()).then(d=>{{
  var el=document.getElementById('agents-list');
  if(!d.agents||!d.agents.length){{el.innerHTML='<span class="empty">No agents in this namespace</span>';}}
  else{{el.innerHTML='<ul class="agent-list">'+d.agents.map(a=>
   '<li><span class="agent-name">'+a.name+'</span>'+
   (a.description?'<span class="agent-desc">'+a.description.slice(0,50)+'</span>':'')+
   '</li>').join('')+'</ul>';}}
  var c=document.getElementById('conv-count');if(c)c.textContent=d.conversations;
 }}).catch(function(){{}});
}}
function submitForm(e){{
 e.preventDefault();
 var btn=document.getElementById('submit-btn');
 var res=document.getElementById('result');
 var data=getFormData();
 if(!data.token){{
  res.innerHTML='<div class="msg err">Enter a bot token first</div>';return false;
 }}
 btn.disabled=true;btn.textContent='Saving...';
 fetch('/api/test',{{
  method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(data)
 }}).then(r=>r.json()).then(td=>{{
  if(td.code!==200){{
   res.innerHTML='<div class="msg err">'+(td.error||'Connection failed')+'</div>';
   btn.disabled=false;btn.textContent='Save & Connect';return;
  }}
  return fetch('/api/configure',{{
   method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(data)
  }}).then(r=>r.json()).then(d=>{{
   if(d.code===200){{
     showConnected(td.bot);
   }}else{{
    res.innerHTML='<div class="msg err">'+(d.error||'Unknown error')+'</div>';
    btn.disabled=false;btn.textContent='Save & Connect';
   }}
  }});
 }}).catch(()=>{{
  res.innerHTML='<div class="msg err">Request failed</div>';
  btn.disabled=false;btn.textContent='Save & Connect';
 }});
 return false;
}}
</script>
</body></html>"""


def _render_connected(bot: dict) -> str:
    username = bot.get("username", "unknown")
    first_name = bot.get("first_name", "")
    link = f"https://t.me/{username}"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={link}"

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Telegram Channel — Ark</title>
<style>{CSS}</style>
</head><body>
<div class="container">
<h1>Ark — Telegram Channel</h1>
<p class="subtitle">Ark agent gateway via Telegram</p>

<div class="card">
 <div class="bot-header">
  <span class="dot ok"></span>
  <div>
   <div class="bot-name">@{username}</div>
   <div class="bot-link"><a href="{link}" target="_blank">{link}</a></div>
  </div>
 </div>
 <div class="qr">
  <div class="qr-img">
   <a href="{link}" target="_blank">
    <img src="{qr_url}" alt="QR" onerror="this.parentElement.parentElement.style.display='none'">
   </a>
  </div>
  <div class="qr-text">
   <p class="scan">Scan to chat</p>
   <p>Open Telegram and scan this code, or tap the link. Send /start to pick an agent.</p>
  </div>
 </div>
</div>

<div class="card">
 <h2>Agents</h2>
 <div id="agents-list"><span class="empty">Loading...</span></div>
</div>

<div class="card">
 <h2>Status</h2>
 <div class="stat-row">
  <span class="stat-label">Active conversations</span>
  <span class="stat-value" id="conv-count">&mdash;</span>
 </div>
</div>

<div class="card" id="config-info" style="padding:14px 20px">
 <div style="display:flex;justify-content:space-between;align-items:center">
  <span id="secret-status" style="font-size:12px;color:#ffffff61"></span>
  <span style="font-size:12px;color:#ffffff99">Configuration</span>
 </div>
 <div id="reconfig" style="margin-top:14px">
  <div id="reconfig-result"></div>
  <div class="field">
   <label for="new-token">Bot Token *</label>
   <input type="text" id="new-token" placeholder="123456789:ABCdefGhi...">
  </div>
  <div class="field">
   <label for="new-bridge">Telegram API URL <span style="color:#ffffff61">(optional)</span></label>
   <input type="text" id="new-bridge" placeholder="https://api.telegram.org/bot">
  </div>
  <button class="btn" onclick="saveNewConfig()" id="reconfig-btn" style="font-size:13px;padding:8px 16px">Update</button>
 </div>
</div>
<div class="docs-link" style="margin-top:8px">
 Telegram Channel v0.1.0 &middot;
 <a href="https://github.com/mckinsey/agents-at-scale-marketplace" target="_blank">Open Documentation</a>
</div>
</div>

<script>
fetch('/api/status').then(r=>r.json()).then(d=>{{
 var el=document.getElementById('agents-list');
 if(!d.agents||!d.agents.length){{
  el.innerHTML='<span class="empty">No agents in this namespace</span>';
 }}else{{
  el.innerHTML='<ul class="agent-list">'+d.agents.map(a=>
   '<li><span class="agent-name">'+a.name+'</span>'+
   (a.description?'<span class="agent-desc">'+a.description.slice(0,50)+'</span>':'')+
   '</li>'
  ).join('')+'</ul>';
 }}
 document.getElementById('conv-count').textContent=d.conversations;
 if(d.secret){{
  var s=d.secret;
  var ss=document.getElementById('secret-status');
  if(ss)ss.innerHTML='<code>Secret</code> <code>'+s.namespace+'/'+s.name+'</code> \u2014 '+(s.exists?'configured':'not found');
 }}
}}).catch(()=>{{
 document.getElementById('agents-list').innerHTML='<span class="empty">Failed to load</span>';
}});
function saveNewConfig(){{
 var btn=document.getElementById('reconfig-btn');
 var res=document.getElementById('reconfig-result');
 var data={{token:document.getElementById('new-token').value,bridge_url:document.getElementById('new-bridge').value}};
 if(!data.token){{res.innerHTML='<div class="msg err">Enter a bot token</div>';return;}}
 btn.disabled=true;btn.textContent='Saving...';
 fetch('/api/configure',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(data)}})
 .then(r=>r.json()).then(d=>{{
  if(d.code===200){{
   res.innerHTML='<div class="msg ok">'+d.message+'</div>';
   btn.textContent='Saved';
  }}else{{
   res.innerHTML='<div class="msg err">'+(d.error||'Error')+'</div>';
   btn.disabled=false;btn.textContent='Save';
  }}
 }}).catch(()=>{{res.innerHTML='<div class="msg err">Request failed</div>';btn.disabled=false;btn.textContent='Save';}});
}}
</script>
</body></html>"""
