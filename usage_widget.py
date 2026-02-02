#!/usr/bin/env python3
"""
Floating Usage Widget - Always-on-top mini window showing AI quota status.
"""

import tkinter as tk
import sys
import os
import threading
import io
from datetime import datetime
from contextlib import redirect_stdout, redirect_stderr

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Change working directory to script location (needed for shortcuts)
os.chdir(SCRIPT_DIR)

# Add script directory to Python path for imports
sys.path.insert(0, SCRIPT_DIR)


def safe_import_antigravity():
    try:
        from antigravity_checker import get_valid_token, load_code_assist, fetch_available_models
        return get_valid_token, load_code_assist, fetch_available_models
    except Exception:
        return None, None, None


def safe_import_claude():
    try:
        from claude_checker import load_credentials, fetch_usage
        return load_credentials, fetch_usage
    except Exception:
        return None, None


def format_reset_time(reset_time_str):
    """Format reset time as HH:MM (~remaining)"""
    if not reset_time_str:
        return ""
    try:
        reset_time = datetime.fromisoformat(reset_time_str.replace('Z', '+00:00'))
        local_reset = reset_time.astimezone()
        time_str = local_reset.strftime('%H:%M')
        
        # Calculate remaining time
        now = datetime.now(local_reset.tzinfo)
        remaining = local_reset - now
        total_seconds = int(remaining.total_seconds())
        
        if total_seconds <= 0:
            return time_str
        
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        
        # Format remaining time
        if days > 0:
            remaining_str = f"~{days}D{hours}h{minutes}m"
        elif hours > 0:
            remaining_str = f"~{hours}h{minutes}m" if minutes > 0 else f"~{hours}h"
        else:
            remaining_str = f"~{minutes}m"
        
        return f"{time_str} ({remaining_str})"
    except:
        return ""


class UsageWidget:
    REFRESH_INTERVAL = 60000
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AI Usage")
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)
        try:
            self.root.attributes('-alpha', 0.95)
        except:
            pass
        
        # Colors
        self.bg = '#1e1e2e'
        self.fg = '#cdd6f4'
        self.accent = '#89b4fa'
        self.green = '#a6e3a1'
        self.yellow = '#f9e2af'
        self.red = '#f38ba8'
        self.dim = '#6c7086'
        self.bar_bg = '#45475a'
        
        self.root.configure(bg=self.bg)
        
        self.frame = tk.Frame(self.root, bg=self.bg, highlightbackground='#45475a', highlightthickness=1)
        self.frame.pack(fill='both', expand=True)
        
        # Title bar
        title_bar = tk.Frame(self.frame, bg='#313244', height=22)
        title_bar.pack(fill='x')
        title_bar.pack_propagate(False)
        
        self.title_lbl = tk.Label(title_bar, text="⚡ AI Usage", bg='#313244', 
                                   fg=self.accent, font=('Segoe UI', 8, 'bold'))
        self.title_lbl.pack(side='left', padx=6)
        
        close_btn = tk.Label(title_bar, text="✕", bg='#313244', fg=self.dim, 
                              font=('Segoe UI', 9), cursor='hand2')
        close_btn.pack(side='right', padx=6)
        close_btn.bind('<Button-1>', lambda e: self.root.destroy())
        close_btn.bind('<Enter>', lambda e: close_btn.configure(fg=self.red))
        close_btn.bind('<Leave>', lambda e: close_btn.configure(fg=self.dim))
        
        self.refresh_btn = tk.Label(title_bar, text="↻", bg='#313244', fg=self.dim, 
                                     font=('Segoe UI', 10), cursor='hand2')
        self.refresh_btn.pack(side='right', padx=2)
        self.refresh_btn.bind('<Button-1>', lambda e: self.refresh_data())
        self.refresh_btn.bind('<Enter>', lambda e: self.refresh_btn.configure(fg=self.accent))
        self.refresh_btn.bind('<Leave>', lambda e: self.refresh_btn.configure(fg=self.dim))
        
        # Drag
        self._drag_x = self._drag_y = 0
        for w in [title_bar, self.title_lbl]:
            w.bind('<Button-1>', lambda e: setattr(self, '_drag_x', e.x) or setattr(self, '_drag_y', e.y))
            w.bind('<B1-Motion>', lambda e: self.root.geometry(f'+{self.root.winfo_x()+e.x-self._drag_x}+{self.root.winfo_y()+e.y-self._drag_y}'))
        
        # Content
        self.content = tk.Frame(self.frame, bg=self.bg)
        self.content.pack(fill='both', expand=True, padx=8, pady=6)
        
        self.rows = {}
        
        # Antigravity section header
        ag_header = tk.Label(self.content, text="Antigravity", bg=self.bg, fg=self.accent, 
                              font=('Segoe UI', 8, 'bold'), anchor='w')
        ag_header.grid(row=0, column=0, columnspan=3, sticky='w', pady=(0, 2))
        
        # Antigravity groups
        self._create_row("ag_claude", "Claude", 1)
        self._create_row("ag_gemini", "G3 Pro", 2)
        self._create_row("ag_flash", "G3 Flash", 3)
        self._create_row("ag_nano", "Nano 🍌", 4)
        
        # Separator
        tk.Frame(self.content, bg=self.bar_bg, height=1).grid(row=5, column=0, columnspan=3, sticky='ew', pady=4)
        
        # Claude Code section header
        cc_header = tk.Label(self.content, text="Claude Code", bg=self.bg, fg=self.accent, 
                              font=('Segoe UI', 8, 'bold'), anchor='w')
        cc_header.grid(row=6, column=0, columnspan=3, sticky='w', pady=(2, 2))
        
        # Claude Code rows
        self._create_row("cc_5h", "5 Hour", 7)
        self._create_row("cc_7d", "7 Day", 8)
        
        # Update label
        self.update_lbl = tk.Label(self.content, text="", bg=self.bg, fg=self.dim, font=('Segoe UI', 7))
        self.update_lbl.grid(row=9, column=0, columnspan=3, sticky='e', pady=(4, 0))
        
        # Size & position
        self.root.update_idletasks()
        w, h = 250, 235
        x = self.root.winfo_screenwidth() - w - 20
        y = self.root.winfo_screenheight() - h - 60
        self.root.geometry(f'{w}x{h}+{x}+{y}')
        
        self.root.after(500, self.refresh_data)
        self.schedule_refresh()
    
    def _create_row(self, key, title, row):
        # Name label
        name_lbl = tk.Label(self.content, text=title, bg=self.bg, fg=self.fg, 
                             font=('Segoe UI', 8), anchor='w', width=8)
        name_lbl.grid(row=row, column=0, sticky='w')
        
        # Progress bar container
        bar_frame = tk.Frame(self.content, bg=self.bar_bg, height=14)
        bar_frame.grid(row=row, column=1, sticky='ew', padx=4, pady=2)
        self.content.columnconfigure(1, weight=1, minsize=80)
        
        # Progress fill
        bar_fill = tk.Frame(bar_frame, bg=self.green, height=14)
        bar_fill.place(x=0, y=0, relwidth=0, relheight=1)
        
        # Percentage text centered on bar
        pct_lbl = tk.Label(bar_frame, text="--", bg=self.bar_bg, fg=self.fg, 
                            font=('Segoe UI', 7, 'bold'))
        pct_lbl.place(relx=0.5, rely=0.5, anchor='center')
        
        # Reset time on the right
        reset_lbl = tk.Label(self.content, text="", bg=self.bg, fg=self.dim, 
                              font=('Segoe UI', 7), anchor='e')
        reset_lbl.grid(row=row, column=2, sticky='e', padx=(2, 0))
        
        self.rows[key] = {'fill': bar_fill, 'pct': pct_lbl, 'reset': reset_lbl, 'bar_frame': bar_frame}
    
    def get_color(self, pct):
        if pct < 50: return self.green
        if pct < 80: return self.yellow
        return self.red
    
    def update_row(self, key, pct, reset="", error=None):
        r = self.rows.get(key)
        if not r:
            return
        
        if error:
            r['fill'].place(relwidth=0)
            r['pct'].configure(text=error, bg=self.bar_bg, fg=self.red)
            r['reset'].configure(text="")
        else:
            pct = float(pct) if pct else 0
            color = self.get_color(pct)
            r['fill'].configure(bg=color)
            r['fill'].place(relwidth=min(pct, 100) / 100)
            # Text bg matches fill when bar covers center (50%+), fg goes dark for contrast
            text_bg = color if pct >= 50 else self.bar_bg
            text_fg = '#1e1e2e' if pct >= 50 else self.fg
            r['pct'].configure(text=f"{pct:.0f}%", bg=text_bg, fg=text_fg)
            r['reset'].configure(text=reset if reset else "")
    
    def refresh_data(self):
        self.refresh_btn.configure(fg=self.accent)
        threading.Thread(target=self._fetch_data, daemon=True).start()
    
    def _fetch_data(self):
        ag = self._get_antigravity_data()
        cc = self._get_claude_data()
        self.root.after(0, lambda: self._update_ui(ag, cc))
    
    def _get_antigravity_data(self):
        get_valid_token, load_code_assist, fetch_available_models = safe_import_antigravity()
        if not get_valid_token:
            return {'error': 'No module'}
        try:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                tokens = get_valid_token()
            if not tokens:
                return {'error': 'Login'}
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                code_assist, _ = load_code_assist(tokens['access_token'])
                cap = code_assist.get('cloudaicompanionProject')
                pid = cap if isinstance(cap, str) else cap.get('id') if isinstance(cap, dict) else None
                models, _ = fetch_available_models(tokens['access_token'], pid)
            
            groups = {
                'claude': {'pat': ['claude', 'gpt-oss'], 'pct': 0, 'rst': ''},
                'gemini': {'pat': ['gemini-3-pro-high', 'gemini-3-pro-low'], 'pct': 0, 'rst': ''},
                'flash': {'pat': ['gemini-3-flash'], 'pct': 0, 'rst': ''},
                'nano': {'pat': ['gemini-3-pro-image'], 'pct': 0, 'rst': ''},
            }
            for mid, info in models.get('models', {}).items():
                if info.get('isInternal'):
                    continue
                q = info.get('quotaInfo', {})
                # Check for exhausted state: explicit flag OR missing remainingFraction
                if q.get('isExhausted') or 'remainingFraction' not in q:
                    used = 100.0
                else:
                    used = (1 - q.get('remainingFraction', 1.0)) * 100
                rst = q.get('resetTime', '')
                for g in groups.values():
                    if any(p in mid.lower() for p in g['pat']):
                        # Always capture reset time if available, update pct if higher
                        if not g['rst'] and rst:
                            g['rst'] = rst
                        if used > g['pct']:
                            g['pct'] = used
                            if rst:
                                g['rst'] = rst
            return {'groups': groups}
        except Exception as e:
            return {'error': str(e)[:20]}
    
    def _get_claude_data(self):
        load_credentials, fetch_usage = safe_import_claude()
        if not load_credentials:
            return {'error': 'No module'}
        try:
            result = load_credentials()
            if not result or not result[0]:
                return {'error': 'Login'}
            usage, err = fetch_usage(result[0])
            if err or not usage:
                return {'error': 'API error'}
            
            fh = usage.get('five_hour') or {}
            sd = usage.get('seven_day') or {}
            
            return {
                '5h_pct': fh.get('utilization', 0) or 0,
                '5h_rst': fh.get('resets_at', ''),
                '7d_pct': sd.get('utilization', 0) or 0,
                '7d_rst': sd.get('resets_at', ''),
            }
        except Exception as e:
            return {'error': str(e)[:12]}
    
    def _update_ui(self, ag, cc):
        # Antigravity groups
        if 'error' in ag:
            for k in ['ag_claude', 'ag_gemini', 'ag_flash', 'ag_nano']:
                self.update_row(k, 0, error=ag['error'])
        else:
            for wk, gk in [('ag_claude', 'claude'), ('ag_gemini', 'gemini'), 
                           ('ag_flash', 'flash'), ('ag_nano', 'nano')]:
                g = ag['groups'][gk]
                self.update_row(wk, g['pct'], format_reset_time(g['rst']))
        
        # Claude Code
        if 'error' in cc:
            self.update_row('cc_5h', 0, error=cc['error'])
            self.update_row('cc_7d', 0, error=cc['error'])
        else:
            self.update_row('cc_5h', cc['5h_pct'], format_reset_time(cc['5h_rst']))
            self.update_row('cc_7d', cc['7d_pct'], format_reset_time(cc['7d_rst']))
        
        self.update_lbl.configure(text=f"Updated {datetime.now().strftime('%H:%M')}")
        self.refresh_btn.configure(fg=self.dim)
    
    def schedule_refresh(self):
        self.root.after(self.REFRESH_INTERVAL, lambda: (self.refresh_data(), self.schedule_refresh()))
    
    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    try:
        UsageWidget().run()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter...")
