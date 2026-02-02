#!/usr/bin/env python3
"""
Check your Claude Code usage limits.
Features:
- Reads OAuth tokens from Claude Code credentials
- Shows 5-hour, 7-day, and 7-day Sonnet rate limits
- Token caching with auto-refresh support
- Simple CLI interface

Usage:
    python claude_checker.py           # Check usage (shows login hint if needed)
    python claude_checker.py --raw     # Show raw API response as JSON
    python claude_checker.py --help    # Show help
"""

import json
import os
import sys
import platform
from pathlib import Path
from datetime import datetime
from urllib.parse import urlencode

# Fix Windows console encoding
if sys.platform == 'win32':
    # Enable UTF-8 mode on Windows
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    # Also try to enable ANSI escape sequences on Windows 10+
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

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

VERSION = '1.0.0'

# Detect platform for user agent
_os = platform.system().lower()
_arch = platform.machine().lower()
if _arch in ('x86_64', 'amd64'):
    _arch = 'amd64'
elif _arch in ('arm64', 'aarch64'):
    _arch = 'arm64'
USER_AGENT = f'claude-checker/{VERSION} {_os}/{_arch}'

# API Config
API_USAGE_URL = 'https://api.anthropic.com/api/oauth/usage'
API_BETA_HEADER = 'oauth-2025-04-20'

# Check if terminal supports Unicode (fallback to ASCII)
def supports_unicode():
    """Check if terminal supports Unicode characters"""
    try:
        '█░'.encode(sys.stdout.encoding or 'utf-8')
        return True
    except (UnicodeEncodeError, LookupError):
        return False

USE_UNICODE = supports_unicode()

# =============================================================================
# Credential Storage
# =============================================================================

def get_credentials_path():
    """Get path to Claude Code credentials file"""
    if sys.platform == 'win32':
        home = os.environ.get('USERPROFILE', os.path.expanduser('~'))
    else:
        home = os.path.expanduser('~')
    return Path(home) / '.claude' / '.credentials.json'

def load_credentials():
    """Load OAuth access token from Claude Code credentials"""
    creds_path = get_credentials_path()
    
    if not creds_path.exists():
        return None, f"Credentials file not found at: {creds_path}"
    
    try:
        with open(creds_path, 'r') as f:
            data = json.load(f)
        
        # Extract OAuth token
        oauth_data = data.get('claudeAiOauth', {})
        access_token = oauth_data.get('accessToken')
        
        if not access_token:
            return None, "No access token found in credentials. Please login to Claude Code first."
        
        return access_token, None
        
    except json.JSONDecodeError as e:
        return None, f"Failed to parse credentials file: {e}"
    except IOError as e:
        return None, f"Failed to read credentials file: {e}"

# =============================================================================
# HTTP Helpers
# =============================================================================

def http_get(url, headers=None):
    """Make HTTP GET request"""
    headers = headers or {}
    
    if HAS_REQUESTS:
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            return resp.status_code, resp.text
        except requests.RequestException as e:
            return None, str(e)
    else:
        req = urllib.request.Request(url, headers=headers, method='GET')
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status, resp.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode('utf-8')
        except urllib.error.URLError as e:
            return None, str(e)

# =============================================================================
# API Calls
# =============================================================================

def fetch_usage(access_token):
    """Fetch usage limits from Anthropic API"""
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': USER_AGENT,
        'Authorization': f'Bearer {access_token}',
        'anthropic-beta': API_BETA_HEADER,
    }
    
    status, response = http_get(API_USAGE_URL, headers)
    
    if status is None:
        return None, f"Network error: {response}"
    
    if status == 401:
        return None, "Authentication failed. Your token may have expired. Please re-login to Claude Code."
    
    if status != 200:
        return None, f"API error: HTTP {status}"
    
    try:
        return json.loads(response), None
    except json.JSONDecodeError as e:
        return None, f"Failed to parse API response: {e}"

# =============================================================================
# Display
# =============================================================================

def format_time_until(reset_time_str):
    """Format time until reset with local time in 24hr format"""
    if not reset_time_str:
        return "-"
    
    try:
        reset_time = datetime.fromisoformat(reset_time_str.replace('Z', '+00:00'))
        now = datetime.now(reset_time.tzinfo)
        diff = reset_time - now
        
        # Convert to local time for display
        local_reset = reset_time.astimezone()
        local_time_str = local_reset.strftime('%H:%M')
        
        if diff.total_seconds() <= 0:
            return f"now ({local_time_str})"
        
        total_seconds = int(diff.total_seconds())
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        
        if days > 0:
            return f"{days}d{hours}h ({local_time_str})"
        if hours > 0:
            return f"{hours}h{minutes}m ({local_time_str})"
        return f"{minutes}m ({local_time_str})"
    except Exception:
        return "?"

def get_color_code(utilization_pct):
    """Get ANSI color code based on utilization percentage (0-100)"""
    if utilization_pct < 50:
        return '\033[92m'  # Green
    elif utilization_pct < 80:
        return '\033[93m'  # Yellow
    else:
        return '\033[91m'  # Red

def create_progress_bar(utilization_pct, width=10):
    """Create a visual progress bar from percentage (0-100)"""
    # Cap utilization at 100% for display
    capped = min(utilization_pct / 100.0, 1.0)
    filled = int(capped * width)
    empty = width - filled
    if USE_UNICODE:
        return '█' * filled + '░' * empty
    else:
        return '#' * filled + '-' * empty

def display_usage(usage_data, show_raw=False):
    """Display usage information"""
    
    # Show raw JSON if requested
    if show_raw:
        print("\n=== RAW API RESPONSE ===")
        print(json.dumps(usage_data, indent=2))
        return
    
    reset = '\033[0m'
    bold = '\033[1m'
    dim = '\033[2m'
    
    print()
    print("=" * 70)
    print(f"{bold}  CLAUDE CODE USAGE STATUS{reset}")
    print("=" * 70)
    
    # Rate limit sections
    limits = [
        ('five_hour', '5-Hour Limit', '5h'),
        ('seven_day', '7-Day All Models', '7d'),
        ('seven_day_sonnet', '7-Day Sonnet Only', '7d-S'),
    ]
    
    print()
    
    for key, label, short in limits:
        data = usage_data.get(key)
        
        if data is None:
            print(f"  {dim}{short}: Not available{reset}")
            continue
        
        utilization = data.get('utilization', 0)
        resets_at = data.get('resets_at')
        
        # utilization is already a percentage (0-100) from the API
        pct = utilization
        remaining_pct = 100 - utilization
        
        # Color coding
        color = get_color_code(utilization)
        
        # Progress bar
        bar = create_progress_bar(utilization)
        
        # Reset time
        reset_str = format_time_until(resets_at)
        
        # Status indicator
        if utilization >= 100:
            status = "EXHAUSTED"
        elif utilization >= 90:
            status = "CRITICAL"
        elif utilization >= 80:
            status = "WARNING"
        else:
            status = ""
        
        # Display line
        print(f"  {bold}{label}{reset}")
        print(f"    {color}{bar}{reset}  {pct:5.1f}% used  |  {remaining_pct:5.1f}% remaining  |  Resets in: {reset_str}", end="")
        if status:
            print(f"  {color}[{status}]{reset}")
        else:
            print()
        print()
    
    # Legend
    print("-" * 70)
    print(f"  {dim}Color Legend:{reset} ", end="")
    print(f"\033[92m●{reset} Safe (0-50%)  ", end="")
    print(f"\033[93m●{reset} Warning (50-80%)  ", end="")
    print(f"\033[91m●{reset} Critical (80-100%)")
    print()

# =============================================================================
# Main
# =============================================================================

def check_usage(show_raw=False):
    """Main function to check usage"""
    
    # Load credentials
    token, err = load_credentials()
    if err:
        print(f"\n[!] {err}")
        print("\n    To login, run Claude Code and use /login command.")
        return 1
    
    print("\n[*] Loading Claude Code usage...")
    
    # Fetch usage
    usage, err = fetch_usage(token)
    if err:
        print(f"\n[!] Failed to fetch usage: {err}")
        return 1
    
    display_usage(usage, show_raw)
    return 0

def main():
    """Entry point"""
    args = sys.argv[1:]
    
    # Check for flags
    show_raw = '--raw' in args or '--json' in args
    args = [a for a in args if a not in ('--raw', '--json')]
    
    if args:
        command = args[0].lower()
        
        if command in ['-h', '--help', 'help']:
            print(__doc__)
            print("\nOptions:")
            print("  --raw, --json    Show raw API response as JSON")
            return 0
        else:
            print(f"Unknown command: {command}")
            print("Usage: python claude_checker.py [--raw|--help]")
            return 1
    
    return check_usage(show_raw)

if __name__ == '__main__':
    sys.exit(main())
