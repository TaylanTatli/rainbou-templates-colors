#!/usr/bin/env python3
import os
import sys
import tty
import termios
import time
import fcntl
import shutil
import signal

THEME_DIR = os.path.expanduser("~/.config/rainbou/colors")

class ResizeEvent(Exception):
    pass

def handle_resize(signum, frame):
    raise ResizeEvent()

def load_themes():
    themes = []
    if not os.path.exists(THEME_DIR):
        return themes
        
    for filename in sorted(os.listdir(THEME_DIR)):
        filepath = os.path.join(THEME_DIR, filename)
        if os.path.isfile(filepath):
            parsed = parse_theme(filepath, filename)
            if parsed['colors']: 
                themes.append(parsed)
    return themes

def parse_theme(filepath, filename):
    theme = {
        'filename': filename,
        'metadata': {'name': filename},
        'colors': {}
    }
    try:
        with open(filepath, 'r') as f:
            section = None
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'): continue
                
                if line.startswith('metadata:'): section = 'metadata'
                elif line.startswith('colors:'): section = 'colors'
                elif ':' in line:
                    key, val = line.split(':', 1)
                    key = key.strip()
                    val = val.strip().strip(' "\'')
                    if section == 'metadata':
                        theme['metadata'][key] = val
                    elif section == 'colors':
                        theme['colors'][key] = val
    except Exception:
        pass
    return theme

# --- ANSI COLORS AND CONTROL CODES ---
def rgb_bg(r, g, b): return f"\033[48;2;{r};{g};{b}m"
def rgb_fg(r, g, b): return f"\033[38;2;{r};{g};{b}m"
RESET = "\033[0m"
CLEAR = "\033[2J"
HOME = "\033[H"
HIDE = "\033[?25l"
SHOW = "\033[?25h"
ERASE_EOL = "\033[K" 

def get_c(key, default, theme):
    h = theme['colors'].get(key, default).lstrip('#')
    try: return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    except: return (0,0,0)

def draw_screen(themes, selected_idx, window_start):
    cols, rows = shutil.get_terminal_size()
    
    # Left panel colors
    ui_bg = (30, 30, 40) 
    ui_fg = (200, 200, 200)
    
    if not themes:
        sys.stdout.write(CLEAR + HOME + "Tema bulunamadı.\r\n")
        return

    theme = themes[selected_idx]
    th_bg = get_c('bg', '000000', theme)
    th_fg = get_c('fg', 'ffffff', theme)

    frame = []
    
    # Top Header
    header_text = " 👻 Rainbou Theme Preview 👻 "
    pad_left = max(0, (cols - len(header_text)) // 2)
    frame.append(HOME + rgb_bg(45, 45, 60) + rgb_fg(255, 255, 255) + (" " * pad_left) + header_text + ERASE_EOL)

    list_width = 32
    
    for r in range(1, rows):
        line = ""
        list_item_idx = window_start + (r - 1)
        
        # --- LEFT PANEL (List) ---
        if list_item_idx < len(themes):
            name = themes[list_item_idx]['metadata'].get('name', themes[list_item_idx]['filename'])
            if len(name) > list_width - 4: 
                name = name[:list_width-4] + ".."
            
            if list_item_idx == selected_idx:
                line += rgb_bg(80, 80, 95) + rgb_fg(130, 255, 130) + f" ❯ {name:<{list_width-3}}"
            else:
                line += rgb_bg(*ui_bg) + rgb_fg(*ui_fg) + f"   {name:<{list_width-3}}"
        else:
            line += rgb_bg(*ui_bg) + (" " * list_width)
            
        # --- RIGHT PANEL (Preview) ---
        p_line = "  "
        rel_r = r - 2
        
        if rel_r == 1: p_line += f"  {theme['metadata'].get('name', theme['filename'])}"
        elif rel_r == 2: p_line += f"  {THEME_DIR}/{theme['filename']}"
        elif rel_r == 5:
            p_line += "  "
            for i in range(8):
                c = get_c(f"0{i}", "000000", theme)
                p_line += f"{i:<2} {rgb_bg(*c)}    {rgb_bg(*th_bg)}  "
        elif rel_r == 7:
            p_line += "  "
            for i in range(8, 16):
                k = f"{i:02d}" if i < 10 else str(i)
                c = get_c(k, "000000", theme)
                p_line += f"{i:<2} {rgb_bg(*c)}    {rgb_bg(*th_bg)}  "
                
        # Code Block Simulation
        elif rel_r >= 10 and rel_r <= 23:
            idx = rel_r - 10
            
            kw = rgb_fg(*get_c('05', 'ffffff', theme)) # Purple (Keyword)
            fn = rgb_fg(*get_c('02', 'ffffff', theme)) # Green (Function)
            st = rgb_fg(*get_c('03', 'ffffff', theme)) # Yellow (String)
            ty = rgb_fg(*get_c('04', 'ffffff', theme)) # Blue (Type/Paket)
            cn = rgb_fg(*get_c('06', 'ffffff', theme)) # Cyan (Sayı/Bool/Nil)
            gy = rgb_fg(*get_c('08', 'ffffff', theme)) # Gray (Border/Comment)
            nm = rgb_fg(*th_fg)                        # Normal Text

            it = "\033[3m"     # Start italic
            no_it = "\033[23m" # End italic
            
            code_lines = [
                f"{gy} ───────┬────────────────────────────────────────────────{nm}",
                f"{gy}        │{nm} File: {nm}rainbou.go",
                f"{gy} ───────┼────────────────────────────────────────────────{nm}",
                f"{gy}   1    │ {gy}{it}// ParseHex validates and parses the color code{no_it}{nm}",
                f"{gy}   2    │{nm} {kw}func{nm} {fn}ParseHex{nm}(hex {ty}string{nm}) ({ty}Color{nm}, {ty}error{nm}) {{",
                f"{gy}   3    │{nm}     {kw}if{nm} {fn}len{nm}(hex) != {cn}6{nm} {{",
                f"{gy}   4    │{nm}         {kw}return{nm} {cn}nil{nm}, {ty}fmt{nm}.{fn}Errorf{nm}({st}\"invalid: %s\"{nm}, hex)",
                f"{gy}   5    │{nm}     }}",
                f"{gy}   6    │{nm}",
                f"{gy}   7    │{nm}     isDark := {cn}true{nm}",
                f"{gy}   8    │{nm}     {kw}return{nm} &{ty}Color{nm}{{",
                f"{gy}   9    │{nm}         Hex:    hex[{cn}0{nm}:{cn}2{nm}],",
                f"{gy}  10    │{nm}         Active: isDark,",
                f"{gy}  11    │{nm}     }}, {cn}nil{nm}"
            ]
            
            if idx < len(code_lines):
                p_line += code_lines[idx]

        line += rgb_bg(*th_bg) + rgb_fg(*th_fg) + p_line + ERASE_EOL
        frame.append(line)
        
    sys.stdout.write("\r\n".join(frame) + RESET)
    sys.stdout.flush()

def read_key():
    ch = sys.stdin.read(1)
    if ch == '\x1b':
        fd = sys.stdin.fileno()
        old_flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, old_flags | os.O_NONBLOCK)
        try:
            seq = sys.stdin.read(2)
            # IF nothing follows \x1b, then it is a REAL ESC key press.
            if not seq: 
                return 'esc'
                
            if seq == '[A': return 'up'
            if seq == '[B': return 'down'
            if seq == '[5': sys.stdin.read(1); return 'pgup'
            if seq == '[6': sys.stdin.read(1); return 'pgdown'
            
            # Mouse movement
            if seq == '[<':
                fcntl.fcntl(fd, fcntl.F_SETFL, old_flags)
                mouse_seq = ''
                while True:
                    c = sys.stdin.read(1)
                    mouse_seq += c
                    if c in 'Mm': break
                
                parts = mouse_seq[:-1].split(';')
                cb, cx, cy = int(parts[0]), int(parts[1]), int(parts[2])
                
                if mouse_seq.endswith('M'):
                    if cb == 64: return 'scroll_up'
                    if cb == 65: return 'scroll_down'
                    if cb == 0: return ('click', cx, cy)
                
                return 'ignore'

            return 'ignore' 

        except Exception:
            return 'esc'
        finally:
            fcntl.fcntl(fd, fcntl.F_SETFL, old_flags)
    
    return ch

def main():
    themes = load_themes()
    if not themes:
        print(f"Hata: {THEME_DIR} dizininde renk dosyası bulunamadı.")
        return

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    
    selected_idx = 0
    window_start = 0

    import signal
    signal.signal(signal.SIGWINCH, handle_resize)

    ENABLE_MOUSE = "\033[?1000h\033[?1006h"
    DISABLE_MOUSE = "\033[?1000l\033[?1006l"

    try:
        tty.setraw(fd)
        sys.stdout.write(HIDE + CLEAR + ENABLE_MOUSE) 
        
        last_scroll_time = 0
        
        while True:
            _, rows = shutil.get_terminal_size()
            max_visible = rows - 1 
            
            if selected_idx < window_start:
                window_start = selected_idx
            elif selected_idx >= window_start + max_visible:
                window_start = selected_idx - max_visible + 1

            draw_screen(themes, selected_idx, window_start)
            
            try:
                key = read_key()
            except ResizeEvent:
                continue 
            
            if key in ('esc', 'q'):
                break
            elif key == 'ignore': 
                continue
            elif key in ('up', 'k'):
                selected_idx = max(0, selected_idx - 1)
            elif key in ('down', 'j'):
                selected_idx = min(len(themes) - 1, selected_idx + 1)
            elif key in ('scroll_up', 'scroll_down'):
                now = time.time()
                if now - last_scroll_time > 0.05: 
                    if key == 'scroll_up':
                        selected_idx = max(0, selected_idx - 1)
                    else:
                        selected_idx = min(len(themes) - 1, selected_idx + 1)
                    last_scroll_time = now
                    
            elif key == 'pgup':
                selected_idx = max(0, selected_idx - max_visible)
            elif key == 'pgdown':
                selected_idx = min(len(themes) - 1, selected_idx + max_visible)
            
            elif isinstance(key, tuple) and key[0] == 'click':
                _, cx, cy = key
                if cx <= 32 and cy >= 2:
                    clicked_idx = window_start + (cy - 2)
                    if 0 <= clicked_idx < len(themes):
                        selected_idx = clicked_idx
                
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        sys.stdout.write(DISABLE_MOUSE + SHOW + CLEAR + HOME + RESET)
        sys.stdout.flush()

if __name__ == '__main__':
    main()
