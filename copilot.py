#!/usr/bin/env python3
"""
Check your GitHub Copilot usage limits (Premium).
Features:
- GitHub Device Flow Authentication
- Fetches quota snapshots for Copilot Premium
- Simple CLI interface

Usage:
    python copilot.py           # Check usage (shows login hint if needed)
    python copilot.py --login   # Trigger login flow
    python copilot.py --raw     # Show raw API response as JSON
"""

import json
import os
import sys
import time
import platform
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path

# Try to use requests if available, otherwise use urllib
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# =============================================================================
# Configuration
# =============================================================================

# VS Code Client ID for Copilot
CLIENT_ID = '01ab8ac9400c4e429b23'
SCOPE = 'read:user'

DEVICE_CODE_URL = 'https://github.com/login/device/code'
ACCESS_TOKEN_URL = 'https://github.com/login/oauth/access_token'
USAGE_URL = 'https://api.github.com/copilot_internal/user'

BASE_HEADERS = {
    'Editor-Version': 'vscode/1.107.0',
    'Editor-Plugin-Version': 'copilot-chat/0.35.0',
    'User-Agent': 'GitHubCopilotChat/0.35.0',
    'Accept': 'application/json',
    'Copilot-Integration-Id': 'vscode-chat'
}

# =============================================================================
# Helpers
# =============================================================================

def get_credentials_path():
    """Get path to Copilot credentials file"""
    if sys.platform == 'win32':
        home = os.environ.get('USERPROFILE', os.path.expanduser('~'))
    else:
        home = os.path.expanduser('~')
    return Path(home) / '.copilot_credentials.json'

def load_credentials():
    """Load OAuth token from credentials file"""
    creds_path = get_credentials_path()
    if not creds_path.exists():
        return None
    try:
        with open(creds_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('access_token')
    except Exception:
        return None

def save_credentials(token_data):
    """Save OAuth token to credentials file"""
    creds_path = get_credentials_path()
    # Ensure directory exists
    creds_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(creds_path, 'w', encoding='utf-8') as f:
            json.dump(token_data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving credentials: {e}")
        return False

def http_post(url, data=None, headers=None, json_resp=True):
    """Make HTTP POST request"""
    headers = headers or {}
    headers['Accept'] = 'application/json'
    
    if HAS_REQUESTS:
        try:
            resp = requests.post(url, json=data, headers=headers, timeout=30)
            if json_resp:
                return resp.status_code, resp.json()
            return resp.status_code, resp.text
        except requests.RequestException as e:
            return None, str(e)
    else:
        # Urllib fallback
        import json as json_lib
        encoded_data = json_lib.dumps(data).encode('utf-8')
        headers['Content-Type'] = 'application/json'
        
        req = urllib.request.Request(url, data=encoded_data, headers=headers, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                content = resp.read().decode('utf-8')
                if json_resp:
                    return resp.status, json.loads(content)
                return resp.status, content
        except urllib.error.HTTPError as e:
            content = e.read().decode('utf-8')
            try:
                return e.code, json.loads(content)
            except:
                return e.code, content
        except Exception as e:
            return None, str(e)

def http_get(url, token=None, headers=None):
    """Make HTTP GET request"""
    headers = headers or {}
    headers.update(BASE_HEADERS)
    headers['X-Github-Api-Version'] = '2025-04-01'
    
    if token:
        headers['Authorization'] = f'token {token}' if not token.startswith('tid=') else f'Bearer {token}'
    
    if HAS_REQUESTS:
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 200:
                return 200, resp.json()
            return resp.status_code, resp.text
        except requests.RequestException as e:
            return None, str(e)
    else:
        req = urllib.request.Request(url, headers=headers, method='GET')
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status, json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode('utf-8')
        except Exception as e:
            return None, str(e)

# =============================================================================
# Logic
# =============================================================================

def login():
    """Perform GitHub Device Flow Login"""
    print("Initiating GitHub Device Flow...")
    
    # 1. Request Device Code
    status, data = http_post(DEVICE_CODE_URL, {
        'client_id': CLIENT_ID,
        'scope': SCOPE
    })
    
    if status != 200 or not data.get('device_code'):
        print(f"Error getting device code: {data}")
        return False

    device_code = data['device_code']
    user_code = data['user_code']
    verification_uri = data['verification_uri']
    interval = data.get('interval', 5)
    expires_in = data.get('expires_in', 900)
    
    print(f"\nPlease visit: {verification_uri}")
    print(f"Enter code:   {user_code}")
    print(f"\nWaiting for authorization... (expires in {expires_in}s)")
    
    # 2. Poll for token
    start_time = time.time()
    while time.time() - start_time < expires_in:
        time.sleep(interval)
        
        status, token_data = http_post(ACCESS_TOKEN_URL, {
            'client_id': CLIENT_ID,
            'device_code': device_code,
            'grant_type': 'urn:ietf:params:oauth:grant-type:device_code'
        })
        
        if status == 200:
            if 'access_token' in token_data:
                print("\nSuccess! Logged in.")
                return save_credentials(token_data)
            elif token_data.get('error') == 'authorization_pending':
                continue
            elif token_data.get('error') == 'slow_down':
                interval += 5
                continue
            else:
                print(f"\nError: {token_data.get('error_description')}")
                return False
                
    print("\nTimed out.")
    return False

def fetch_usage(access_token):
    """Fetch Copilot usage"""
    status, data = http_get(USAGE_URL, access_token)
    
    if status != 200:
        return None, f"API Error {status}: {data}"
        
    return data, None

def display_usage(usage_data, show_raw=False):
    """Display Copilot usage"""
    if show_raw:
        print(json.dumps(usage_data, indent=2))
        return

    print("\n" + "="*50)
    print("  GITHUB COPILOT USAGE")
    print("="*50 + "\n")
    
    # Plan
    plan = usage_data.get('copilot_plan', 'unknown')
    print(f"Plan: {plan.title()}\n")
    
    # Quota Snapshots
    snapshots = usage_data.get('quota_snapshots', {})
    
    items = [
        ('premium_interactions', 'Premium Models')
    ]
    
    for key, label in items:
        item_data = snapshots.get(key)
        if not item_data:
            continue
            
        # Calculate used percentage
        if 'percent_remaining' in item_data:
            used_pct = 100 - item_data['percent_remaining']
        else:
            remaining_pct = item_data.get('remaining_fraction', 0) * 100
            used_pct = 100 - remaining_pct
        
        # Determine raw text
        raw_text = ""
        if item_data.get('unlimited'):
            raw_text = "(Unlimited)"
        elif 'remaining' in item_data and 'entitlement' in item_data:
             rem = int(item_data['remaining'])
             ent = int(item_data['entitlement'])
             raw_text = f"({rem}/{ent} remaining)"
        
        # Bar
        width = 20
        filled = int((used_pct / 100) * width)
        # Clamp filled to 0-20
        filled = max(0, min(width, filled))
        
        bar = '█' * filled + '░' * (width - filled)
        
        color = '\033[92m' # Green
        if used_pct > 50: color = '\033[93m' # Yellow
        if used_pct > 80: color = '\033[91m' # Red
        reset = '\033[0m'
        
        print(f"{label}:")
        print(f"  {color}{bar}{reset} {used_pct:5.1f}% Used {raw_text}")
        print()

def main():
    args = sys.argv[1:]
    
    if '--login' in args:
        login()
        return

    token = load_credentials()
    if not token:
        print("Not logged in. Run 'python copilot.py --login'")
        return

    usage, err = fetch_usage(token)
    if err:
        print(f"Error: {err}")
        # If 401, maybe hint login
        if "401" in str(err):
             print("Try running 'python copilot.py --login'")
        return
        
    display_usage(usage, show_raw='--raw' in args)

if __name__ == '__main__':
    main()
