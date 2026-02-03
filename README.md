# QuotaGremlin 🧌

```
      ⢀⣀⣀⣀⣀⣀⣀⡀
   ⢠⣾⣿⣿⣿⣿⣿⣿⣿⣦⡀
  ⢸⣿⣿⡟⠁  ⠈⢻⣿⣿⡇
  ⢸⣿⣿⣇  👀  ⣸⣿⣿⡇
   ⠻⣿⣿⣷⣦⣤⣴⣾⣿⣿⠟
      ⠉⠻⠿⠿⠿⠿⠟⠋

   QUOTA GREMLIN
  "who ate my tokens?"
```
  
> "The gremlin watching your usage."

A feral, single-file Python script to watch your Antigravity, Claude Code and Github Copilot  AI model quota before it vanishes.

## Features

- **Full OAuth2 Support** - Browser-based Google login
- **Token Caching** - Credentials stored locally, no re-login needed
- **Auto Refresh** - Expired tokens are refreshed automatically
- **Zero Dependencies** - Uses only Python standard library (optional: `requests`)

## Usage

```bash
# Check your quota (login if needed)
python antigravity.py

# Force new login
python antigravity.py login

# Remove stored credentials
python antigravity.py logout

# Show help
python antigravity.py help
```

## Claude Code

Check your Claude Code usage limits (requires Claude Code login).

```bash
# Check usage
python claude.py

# Show raw API response
python claude.py --raw
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
│ 🧌 QuotaGremlin      ↻  ✕ │
├─────────────────────────────┤
│ (◉_◉) "careful..."          │
│                             │
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

A floating desktop widget that displays real-time quota status for Antigravity, Claude Code and Github Copilot.

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

## Refrences

https://github.com/steipete/CodexBar/tree/main/docs

## License

MIT
