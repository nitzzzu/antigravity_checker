# Antigravity Checker

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

## Example Output

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

## License

MIT
