# Antigravity Checker

```
    ___          __  _                       _ __       
   /   |  ____  / /_(_)___ __________ __   _(_) /___  __
  / /| | / __ \/ __/ / __ `/ ___/ __ `/ | / / / __/ / /
 / ___ |/ / / / /_/ / /_/ / /  / /_/ /| |/ / / /_/ /_/ 
/_/  |_/_/ /_/\__/_/\__, /_/   \__,_/ |___/_/\__/\__, /  
                   /____/     Checker           /____/   
```

A simple, single-file Python script to check your Antigravity AI model quota.

## Features

- **Full OAuth2 Support** - Browser-based Google login
- **Token Caching** - Credentials stored locally, no re-login needed
- **Auto Refresh** - Expired tokens are refreshed automatically
- **Zero Dependencies** - Uses only Python standard library (optional: `requests`)

## Usage

```bash
# Check your quota (login if needed)
python antigravity_checker.py

# Force new login
python antigravity_checker.py login

# Remove stored credentials
python antigravity_checker.py logout

# Show help
python antigravity_checker.py help
```

## Claude Checker

Check your Claude Code usage limits (requires Claude Code login).

```bash
# Check usage
python claude_checker.py

# Show raw API response
python claude_checker.py --raw
```

### Example Output

```
======================================================================
  CLAUDE CODE USAGE STATUS
======================================================================

  5-Hour Limit
    ██████░░░░  27.0% used  |  73.0% remaining  |  Resets in: 4h12m

  7-Day All Models
    ░░░░░░░░░░   0.0% used  |  100.0% remaining  |  Resets in: 6d23h

----------------------------------------------------------------------
  Color Legend: ● Safe (0-50%)  ● Warning (50-80%)  ● Critical (80-100%)
```

## Antigravity Example Output

```
============================================================
  ANTIGRAVITY USAGE STATUS
============================================================

  MODEL QUOTAS:
  --------------------------------------------------------
  Model                          Used         Reset In    
  --------------------------------------------------------
  claude-sonnet-4-5              20%          4h 4m       
  gemini-2.5-flash               0%           4h 59m      
  gemini-2.5-pro                 0%           4h 59m      
  gemini-3-flash                 0%           3h 50m      
  --------------------------------------------------------
```

## How It Works

1. **First Run** - Opens browser for Google OAuth login
2. **Token Exchange** - Exchanges auth code for access/refresh tokens
3. **API Calls** - Calls Google Cloud Code API to fetch quota
4. **Display** - Shows model quotas with usage % and reset times

```
┌─────────────────┐      ┌──────────────────┐      ┌────────────────┐
│  OAuth Login    │ ───> │  Token Storage   │ ───> │  API Request   │
│  (browser)      │      │  (local file)    │      │  (googleapis)  │
└─────────────────┘      └──────────────────┘      └────────────────┘
```

## Data Storage

Credentials are stored locally in your system's config directory:

| OS | Location |
|----|----------|
| **Windows** | `%APPDATA%\antigravity-python\tokens.json` |
| **macOS** | `~/Library/Application Support/antigravity-python/tokens.json` |
| **Linux** | `~/.config/antigravity-python/tokens.json` |

### Stored Data

The `tokens.json` file contains:
- `access_token` - Short-lived API access token
- `refresh_token` - Long-lived token to get new access tokens
- `expires_at` - Unix timestamp when access token expires
- `email` - Your Google account email

> **Security Note:** File permissions are set to user-readable only (0600 on Unix).

## API Endpoints

The script communicates with official Google APIs only:

| Endpoint | Purpose |
|----------|---------|
| `accounts.google.com` | OAuth authentication |
| `oauth2.googleapis.com` | Token exchange/refresh |
| `www.googleapis.com` | User info |
| `cloudcode-pa.googleapis.com` | Quota data |

## Requirements

- Python 3.7+
- No external dependencies (uses `urllib`)
- Optional: `requests` library for better HTTP handling

## Usage Widget

```
┌─────────────────────────────┐
│ ⚡ AI Usage           ↻  ✕ │
├─────────────────────────────┤
│ Antigravity                 │
│ Claude    ████░░░░░░ 40%    │
│ G3 Pro    ██░░░░░░░░ 20%    │
│ G3 Flash  ░░░░░░░░░░  0%    │
│ Nano 🍌   ██░░░░░░░░ 20%    │
├─────────────────────────────┤
│ Claude Code                 │
│ 5 Hour    ███░░░░░░░ 27%    │
│ 7 Day     ░░░░░░░░░░  0%    │
│              Updated 17:45  │
└─────────────────────────────┘
```

A floating desktop widget that displays real-time quota status for both Antigravity and Claude Code.

### Features

- **Always-on-top** - Stays visible while you work
- **Auto-refresh** - Updates every 60 seconds
- **Grouped models** - Claude, G3 Pro, G3 Flash, Nano 🍌
- **Color-coded** - Green (0-50%), Yellow (50-80%), Red (80%+)
- **Reset times** - Shows when quotas reset
- **Draggable** - Position anywhere on screen

### Running the Widget

```bash
# With console (for debugging)
python usage_widget.py

# Without console window (recommended)
pythonw usage_widget.py
```

### Auto-start with Windows

1. Press `Win + R`, type `shell:startup`, press Enter
2. Create a shortcut to `pythonw C:\path\to\usage_widget.py`

## License

MIT
