#!/usr/bin/env python3
"""
Check your Antigravity AI model quota.
Features:
- Full OAuth2 support with Google
- Token caching and auto-refresh
- Simple CLI interface

Usage:
    python antigravity_checker.py           # Check quota (login if needed)
    python antigravity_checker.py login     # Force new login
    python antigravity_checker.py logout    # Remove stored credentials
"""

import json
import os
import sys
import time
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, parse_qs, urlparse
from pathlib import Path
from datetime import datetime

# Try to use requests if available, otherwise use urllib
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.error
    HAS_REQUESTS = False

# =============================================================================
# Configuration
# =============================================================================

# OAuth Config
OAUTH_CONFIG = {
    'client_id': '1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com',
    'client_secret': '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',
    'auth_url': 'https://accounts.google.com/o/oauth2/v2/auth',
    'token_url': 'https://oauth2.googleapis.com/token',
    'userinfo_url': 'https://www.googleapis.com/oauth2/v2/userinfo',
    'scopes': [
        'https://www.googleapis.com/auth/cloud-platform',
        'https://www.googleapis.com/auth/userinfo.email'
    ]
}

# Detect platform for user agent
import platform
_os = platform.system().lower()
_arch = platform.machine().lower()
if _arch in ('x86_64', 'amd64'):
    _arch = 'amd64'
elif _arch in ('arm64', 'aarch64'):
    _arch = 'arm64'
USER_AGENT = f'antigravity/1.15.8 {_os}/{_arch}'

# API Config
API_BASE_URL = 'https://cloudcode-pa.googleapis.com'

# Storage location
def get_config_dir():
    if sys.platform == 'win32':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
    elif sys.platform == 'darwin':
        base = os.path.expanduser('~/Library/Application Support')
    else:
        base = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
    return Path(base) / 'antigravity-python'

CONFIG_DIR = get_config_dir()
TOKENS_FILE = CONFIG_DIR / 'tokens.json'

# =============================================================================
# HTTP Helpers
# =============================================================================

def http_post(url, data=None, json_body=None, headers=None):
    """Make HTTP POST request"""
    headers = headers or {}
    
    if HAS_REQUESTS:
        if json_body:
            resp = requests.post(url, json=json_body, headers=headers, timeout=30)
        else:
            resp = requests.post(url, data=data, headers=headers, timeout=30)
        return resp.status_code, resp.text
    else:
        # urllib fallback
        if json_body:
            body = json.dumps(json_body).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        elif data:
            body = urlencode(data).encode('utf-8')
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        else:
            body = None
            
        req = urllib.request.Request(url, data=body, headers=headers, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status, resp.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode('utf-8')

def http_get(url, headers=None):
    """Make HTTP GET request"""
    headers = headers or {}
    
    if HAS_REQUESTS:
        resp = requests.get(url, headers=headers, timeout=30)
        return resp.status_code, resp.text
    else:
        req = urllib.request.Request(url, headers=headers, method='GET')
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status, resp.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode('utf-8')

# =============================================================================
# Token Storage
# =============================================================================

def save_tokens(tokens):
    """Save tokens to disk"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(TOKENS_FILE, 'w') as f:
        json.dump(tokens, f, indent=2)
    # Set restrictive permissions on Unix
    if sys.platform != 'win32':
        os.chmod(TOKENS_FILE, 0o600)

def load_tokens():
    """Load tokens from disk"""
    if not TOKENS_FILE.exists():
        return None
    try:
        with open(TOKENS_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None

def delete_tokens():
    """Delete stored tokens"""
    if TOKENS_FILE.exists():
        TOKENS_FILE.unlink()
        print("Logged out successfully.")
    else:
        print("No stored credentials found.")

# =============================================================================
# OAuth Flow
# =============================================================================

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback"""
    
    def log_message(self, format, *args):
        pass  # Suppress HTTP logs
    
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        
        if 'code' in query:
            self.server.auth_code = query['code'][0]
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(b'''
                <html><body style="font-family: system-ui; padding: 40px; text-align: center;">
                <h1>Login Successful!</h1>
                <p>You can close this window and return to the terminal.</p>
                </body></html>
            ''')
        else:
            error = query.get('error', ['Unknown error'])[0]
            self.server.auth_code = None
            self.server.auth_error = error
            self.send_response(400)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(f'''
                <html><body style="font-family: system-ui; padding: 40px; text-align: center;">
                <h1>Login Failed</h1>
                <p>Error: {error}</p>
                </body></html>
            '''.encode())

def oauth_login():
    """Perform OAuth login flow"""
    print("\n[*] Starting OAuth login flow...")
    
    # Start local server
    server = HTTPServer(('127.0.0.1', 0), OAuthCallbackHandler)
    port = server.server_address[1]
    redirect_uri = f'http://127.0.0.1:{port}/callback'
    
    # Build auth URL
    params = {
        'client_id': OAUTH_CONFIG['client_id'],
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': ' '.join(OAUTH_CONFIG['scopes']),
        'access_type': 'offline',
        'prompt': 'consent'
    }
    auth_url = f"{OAUTH_CONFIG['auth_url']}?{urlencode(params)}"
    
    print(f"\n[*] Opening browser for Google login...")
    print(f"    If browser doesn't open, visit: {auth_url}\n")
    
    webbrowser.open(auth_url)
    
    # Wait for callback
    server.auth_code = None
    server.auth_error = None
    server.timeout = 120  # 2 minute timeout
    
    print("[*] Waiting for authentication...")
    server.handle_request()
    
    if not server.auth_code:
        print(f"\n[!] Login failed: {getattr(server, 'auth_error', 'No auth code received')}")
        return None
    
    # Exchange code for tokens
    print("[*] Exchanging authorization code for tokens...")
    
    status, response = http_post(OAUTH_CONFIG['token_url'], data={
        'code': server.auth_code,
        'client_id': OAUTH_CONFIG['client_id'],
        'client_secret': OAUTH_CONFIG['client_secret'],
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code'
    })
    
    if status != 200:
        print(f"\n[!] Token exchange failed: {response}")
        return None
    
    token_data = json.loads(response)
    
    # Get user email
    email = get_user_email(token_data['access_token'])
    
    # Store tokens
    tokens = {
        'access_token': token_data['access_token'],
        'refresh_token': token_data.get('refresh_token', ''),
        'expires_at': int(time.time()) + token_data.get('expires_in', 3600),
        'email': email
    }
    
    save_tokens(tokens)
    print(f"\n[+] Login successful! Logged in as: {email or 'Unknown'}")
    
    return tokens

def get_user_email(access_token):
    """Get user email from access token"""
    status, response = http_get(
        OAUTH_CONFIG['userinfo_url'],
        headers={'Authorization': f'Bearer {access_token}'}
    )
    
    if status == 200:
        data = json.loads(response)
        return data.get('email')
    return None

def refresh_access_token(tokens):
    """Refresh expired access token"""
    if not tokens.get('refresh_token'):
        print("[!] No refresh token available. Please login again.")
        return None
    
    print("[*] Refreshing access token...")
    
    status, response = http_post(OAUTH_CONFIG['token_url'], data={
        'refresh_token': tokens['refresh_token'],
        'client_id': OAUTH_CONFIG['client_id'],
        'client_secret': OAUTH_CONFIG['client_secret'],
        'grant_type': 'refresh_token'
    })
    
    if status != 200:
        print(f"[!] Token refresh failed: {response}")
        return None
    
    token_data = json.loads(response)
    
    # Update tokens
    tokens['access_token'] = token_data['access_token']
    tokens['expires_at'] = int(time.time()) + token_data.get('expires_in', 3600)
    
    save_tokens(tokens)
    print("[+] Token refreshed successfully.")
    
    return tokens

def get_valid_token():
    """Get valid access token, refreshing if needed"""
    tokens = load_tokens()
    
    if not tokens:
        tokens = oauth_login()
        if not tokens:
            return None
    
    # Check if expired (with 5 min buffer)
    if tokens.get('expires_at', 0) < time.time() + 300:
        tokens = refresh_access_token(tokens)
        if not tokens:
            # Refresh failed, try fresh login
            tokens = oauth_login()
    
    return tokens

# =============================================================================
# API Calls
# =============================================================================

def load_code_assist(access_token):
    """Call loadCodeAssist API"""
    status, response = http_post(
        f'{API_BASE_URL}/v1internal:loadCodeAssist',
        json_body={'metadata': {'ideType': 'ANTIGRAVITY', 'platform': 'PLATFORM_UNSPECIFIED', 'pluginType': 'GEMINI'}},
        headers={
            'Authorization': f'Bearer {access_token}',
            'User-Agent': USER_AGENT
        }
    )
    
    if status != 200:
        return None, f"API error: {status}"
    
    return json.loads(response), None

def fetch_available_models(access_token, project_id=None):
    """Fetch available models with quota info"""
    body = {'project': project_id} if project_id else {}
    
    status, response = http_post(
        f'{API_BASE_URL}/v1internal:fetchAvailableModels',
        json_body=body,
        headers={
            'Authorization': f'Bearer {access_token}',
            'User-Agent': USER_AGENT
        }
    )
    
    if status != 200:
        return None, f"API error: {status}"
    
    return json.loads(response), None

# =============================================================================
# Display
# =============================================================================

def format_time_until(reset_time_str):
    """Format time until reset"""
    try:
        reset_time = datetime.fromisoformat(reset_time_str.replace('Z', '+00:00'))
        now = datetime.now(reset_time.tzinfo)
        diff = reset_time - now
        
        if diff.total_seconds() <= 0:
            return "now"
        
        hours = int(diff.total_seconds() // 3600)
        minutes = int((diff.total_seconds() % 3600) // 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    except:
        return "?"

def display_quota(models_response, code_assist_response, show_raw=False):
    """Display quota information"""
    
    # Show raw JSON if requested
    if show_raw:
        print("\n=== RAW API RESPONSE ===")
        print("\n--- loadCodeAssist ---")
        print(json.dumps(code_assist_response, indent=2))
        print("\n--- fetchAvailableModels ---")
        print(json.dumps(models_response, indent=2))
        return
    
    print("\n" + "=" * 90)
    print("  ANTIGRAVITY USAGE STATUS")
    print("=" * 90)
    
    # -------------------------------------------------------------------------
    # Plan & Tier Info
    # -------------------------------------------------------------------------
    plan_info = code_assist_response.get('planInfo', {})
    monthly = plan_info.get('monthlyPromptCredits', 0) if plan_info else 0
    available = code_assist_response.get('availablePromptCredits', 0)
    
    current_tier = code_assist_response.get('currentTier', {})
    tier_id = current_tier.get('id', 'unknown')
    tier_name = current_tier.get('name', 'Unknown')
    tier_desc = current_tier.get('description', '')
    
    # Map tier ID to friendly name
    plan_map = {
        'free-tier': 'Free',
        'g1-pro-tier': 'Google AI Pro',
        'g1-ultra-tier': 'Google AI Ultra'
    }
    plan_type = plan_map.get(tier_id, tier_id)
    
    print(f"\n  Plan: {plan_type} ({tier_name})")
    if tier_desc and tier_desc != tier_name:
        print(f"  Description: {tier_desc}")
    
    # Show upgrade info if available
    paid_tier = code_assist_response.get('paidTier', {})
    if paid_tier and tier_id == 'free-tier':
        upgrade_text = current_tier.get('upgradeSubscriptionText', '')
        if upgrade_text:
            # Truncate if too long
            if len(upgrade_text) > 80:
                upgrade_text = upgrade_text[:77] + "..."
            print(f"  Upgrade: {upgrade_text}")
    
    if monthly > 0:
        used = monthly - available
        pct = (used / monthly) * 100
        print(f"  Prompt Credits: {available:,} remaining / {monthly:,} monthly ({pct:.1f}% used)")
    
    # -------------------------------------------------------------------------
    # Model Categories
    # -------------------------------------------------------------------------
    default_agent = models_response.get('defaultAgentModelId', '-')
    command_models = models_response.get('commandModelIds', [])
    tab_models = models_response.get('tabModelIds', [])
    image_models = models_response.get('imageGenerationModelIds', [])
    web_search_models = models_response.get('webSearchModelIds', [])
    
    print(f"\n  Default Agent Model: {default_agent}")
    if command_models:
        print(f"  Command Models: {', '.join(command_models)}")
    if image_models:
        print(f"  Image Gen Models: {', '.join(image_models)}")
    
    # -------------------------------------------------------------------------
    # Models Table
    # -------------------------------------------------------------------------
    models = models_response.get('models', {})
    
    if not models:
        print("\n  No model quota information available.")
        return
    
    # Count stats
    total_models = len(models)
    exhausted_models = sum(1 for m in models.values() if m.get('quotaInfo', {}).get('isExhausted'))
    
    print(f"\n  Total Models: {total_models} ({exhausted_models} exhausted)")
    
    print("\n  MODEL DETAILS:")
    print("  " + "-" * 86)
    print(f"  {'Model':<26} {'Provider':<8} {'Used':<8} {'Reset':<8} {'Context':<9} {'Output':<9} {'Caps':<8}")
    print("  " + "-" * 86)
    
    for model_id, info in sorted(models.items()):
        quota_info = info.get('quotaInfo', {})
        remaining = quota_info.get('remainingFraction', 1.0)
        reset_time = quota_info.get('resetTime', '')
        is_exhausted = quota_info.get('isExhausted', False)
        
        # Provider (shortened)
        provider_raw = info.get('modelProvider', '')
        if 'GOOGLE' in provider_raw:
            provider = 'Google'
        elif 'ANTHROPIC' in provider_raw:
            provider = 'Anthropic'
        elif 'OPENAI' in provider_raw:
            provider = 'OpenAI'
        elif info.get('isInternal'):
            provider = 'Internal'
        else:
            provider = '-'
        
        # Token limits
        max_tokens = info.get('maxTokens')
        max_output = info.get('maxOutputTokens')
        
        # Usage
        used_pct = (1 - remaining) * 100
        used_str = "EXHAUST" if is_exhausted else f"{used_pct:.0f}%"
        reset_str = format_time_until(reset_time) if reset_time else "-"
        
        # Format token counts
        def fmt_tokens(n):
            if not n: return "-"
            if n >= 1000000: return f"{n // 1000000}M"
            if n >= 1000: return f"{n // 1000}K"
            return str(n)
        
        context_str = fmt_tokens(max_tokens)
        output_str = fmt_tokens(max_output)
        
        # Capabilities
        caps = []
        if info.get('supportsThinking'):
            budget = info.get('thinkingBudget', 0)
            caps.append(f"T{budget//1024}K" if budget >= 1024 else "T")
        if info.get('supportsImages'):
            caps.append("I")
        if info.get('supportsVideo'):
            caps.append("V")
        if info.get('recommended'):
            caps.append("*")
        caps_str = ''.join(caps) if caps else "-"
        
        # Truncate model name
        display_name = model_id[:24] + ".." if len(model_id) > 26 else model_id
        
        print(f"  {display_name:<26} {provider:<8} {used_str:<8} {reset_str:<8} {context_str:<9} {output_str:<9} {caps_str:<8}")
    
    print("  " + "-" * 86)
    print("\n  Capabilities: T=Thinking (with budget), I=Images, V=Video, *=Recommended")
    print()

# =============================================================================
# Main
# =============================================================================

def check_quota(show_raw=False):
    """Main function to check quota"""
    tokens = get_valid_token()
    
    if not tokens:
        print("\n[!] Failed to obtain valid credentials.")
        return 1
    
    print(f"\n[*] Checking quota for: {tokens.get('email', 'Unknown')}")
    
    # Load code assist
    code_assist, err = load_code_assist(tokens['access_token'])
    if err:
        print(f"\n[!] Failed to load code assist: {err}")
        return 1
    
    # Extract project ID
    project_id = None
    cap = code_assist.get('cloudaicompanionProject')
    if isinstance(cap, str):
        project_id = cap
    elif isinstance(cap, dict):
        project_id = cap.get('id')
    
    # Fetch models
    models, err = fetch_available_models(tokens['access_token'], project_id)
    if err:
        print(f"\n[!] Failed to fetch models: {err}")
        # Still display what we can
        display_quota({}, code_assist, show_raw)
        return 1
    
    display_quota(models, code_assist, show_raw)
    return 0

def main():
    """Entry point"""
    args = sys.argv[1:]
    
    # Check for flags
    show_raw = '--raw' in args or '--json' in args
    args = [a for a in args if a not in ('--raw', '--json')]
    
    if args:
        command = args[0].lower()
        
        if command == 'login':
            oauth_login()
            return 0
        elif command == 'logout':
            delete_tokens()
            return 0
        elif command in ['-h', '--help', 'help']:
            print(__doc__)
            print("\nOptions:")
            print("  --raw, --json    Show raw API response as JSON")
            return 0
        else:
            print(f"Unknown command: {command}")
            print("Usage: python antigravity_checker.py [login|logout|help] [--raw]")
            return 1
    
    return check_quota(show_raw)

if __name__ == '__main__':
    sys.exit(main())
