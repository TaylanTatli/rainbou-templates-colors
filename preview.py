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

def set_terminal_title(title):
    sys.stdout.write(f'\x1b]2;{title}\x07')
    sys.stdout.flush()

set_terminal_title("👻 Rainbou Theme Preview 👻")

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

# --- GHOSTTY RIGHT PANEL BUILDER ---
def build_right_panel(theme, cols, list_width):
    right_width = cols - list_width
    lines = []
    
    th_bg = get_c('bg', '000000', theme)
    th_fg = get_c('fg', 'ffffff', theme)
    bg_s = rgb_bg(*th_bg)
    fg_s = rgb_fg(*th_fg)
    nm = bg_s + fg_s

    def c(idx): return rgb_fg(*get_c(f"{idx:02d}", "000000", theme))
    def b(idx): return rgb_bg(*get_c(f"{idx:02d}", "000000", theme))

    lines.append("") # 0
    
    name = theme['metadata'].get('name', theme['filename'])
    pad = max(0, (right_width - len(name)) // 2)
    lines.append((" " * pad) + f"\033[1;3m{name}\033[22;23m") # 1
    
    path = f"{THEME_DIR}/{theme['filename']}"
    pad = max(0, (right_width - len(path)) // 2)
    lines.append((" " * pad) + path) # 2
    
    lines.append("") # 3
    
    p1 = "  "
    for i in range(8): p1 += f"{i:<2} {b(i)}    {bg_s}  "
    lines.append(p1) # 4
    lines.append("") # 5
    p2 = "  "
    for i in range(8, 16): p2 += f"{i:<2} {b(i)}    {bg_s}  "
    lines.append(p2) # 6
    
    lines.append("") # 7

    lines.append(f"  {c(2)}→{nm} {c(4)}bat{nm} \033[4m{c(6)}ziggzagg.zig\033[24m{nm}") # 8

    gy = c(8)
    border_len = right_width - 12
    lines.append(f"  {gy}───────┬{'─' * max(0, border_len)}{nm}") # 9
    lines.append(f"  {gy}       │ {nm}File: \033[1mziggzagg.zig\033[22m") # 10
    lines.append(f"  {gy}───────┼{'─' * max(0, border_len)}{nm}") # 11

    c5, c10, c12, c2, c4 = c(5), c(10), c(12), c(2), c(4)
    code = [
        f"{c5}const{nm} std {c5}={nm} {c5}@import{nm}({c10}\"std\"{nm});",
        f"",
        f"{c5}pub fn{nm} {c2}main{nm}() {c5}!{nm}{c12}void{nm} {{",
        f"    {c5}const{nm} stdout {c5}={nm} std.Io.getStdOut().writer();",
        f"    {c5}var{nm} i: {c12}usize{nm} {c5}={nm} {c4}1{nm};",
        f"    {c5}while{nm} (i {c5}<={nm} {c4}16{nm}) : (i {c5}+={nm} {c4}1{nm}) {{",
        f"        {c5}if{nm} (i {c5}%{nm} {c4}15{nm} {c5}=={nm} {c4}0{nm}) {{",
        f"            {c5}try{nm} stdout.writeAll({c10}\"ZiggZagg\\n\"{nm});",
        f"        }} {c5}else if{nm} (i {c5}%{nm} {c4}3{nm} {c5}=={nm} {c4}0{nm}) {{",
        f"            {c5}try{nm} stdout.writeAll({c10}\"Zigg\\n\"{nm});",
        f"        }} {c5}else if{nm} (i {c5}%{nm} {c4}5{nm} {c5}=={nm} {c4}0{nm}) {{",
        f"            {c5}try{nm} stdout.writeAll({c10}\"Zagg\\n\"{nm});",
        f"        }} {c5}else{nm} {{",
        f"            {c5}try{nm} stdout.print({c10}\"{{d}}\\n\"{nm}, .{{i}});",
        f"        }}",
        f"    }}",
        f"}}"
    ]
    for idx, c_line in enumerate(code):
        lines.append(f"  {gy}{idx+1:>4}   │ {nm}{c_line}")

    lines.append(f"  {gy}───────┴{'─' * max(0, border_len)}{nm}")

    lines.append(f"  {c(6)}ghostty {nm}on {c(4)} main {c(1)}[+] {nm}via {c(3)} v0.13.0 {nm}via {c(4)}  impure (ghostty-env){nm}")
    lines.append(f"  {c(4)}✦ {nm}at {c(3)}10:36:15 {c(2)}→{nm}")
    lines.append("")

    lorem = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Cras hendrerit aliquet turpis non dictum. Mauris pulvinar nisl sit amet dui cursus tempus. Pellentesque ut dui justo. Etiam quis magna sagittis nisi pretium consequat vitae ut nisl. Sed at metus id odio pulvinar sodales. Vestibulum sollicitudin, sem id tristique vestibulum, neque ante dictum tortor, in convallis mi enim ac lorem."
    lorem_words = lorem.split()
    l_line = "  "
    for word in lorem_words:
        w_format = word
        if "ipsum" in word: w_format = f"{c(2)}{word}{nm}"
        elif "consectetur" in word: w_format = f"\033[1m{word}\033[22m"
        
        if len(l_line.replace("\033[1m","").replace("\033[22m","").replace(c(2),"").replace(nm,"")) + len(word) + 1 > right_width:
            lines.append(l_line)
            l_line = "  " + w_format + " "
        else:
            l_line += w_format + " "
            
    if l_line.strip():
        lines.append(l_line)

    return lines

def draw_screen(themes, selected_idx, window_start, hover_idx):
    cols, rows = shutil.get_terminal_size()
    
    # Senin ayarladığın sol menü renkleri!
    ui_bg = (30, 30, 30) 
    ui_hover_bg = (50, 50, 50) # Koyu temana uygun hafif hover parlaması
    ui_fg = (250, 250, 250)
    
    if not themes:
        sys.stdout.write(CLEAR + HOME + "Tema bulunamadı.\r\n")
        return

    theme = themes[selected_idx]
    th_bg = get_c('bg', '000000', theme)
    th_fg = get_c('fg', 'ffffff', theme)

    frame = []
    list_width = 32
    
    right_lines = build_right_panel(theme, cols, list_width)
    
    for r in range(rows):
        line = ""
        list_item_idx = window_start + r
        
        # --- LEFT PANEL (List) ---
        if list_item_idx < len(themes):
            name = themes[list_item_idx]['metadata'].get('name', themes[list_item_idx]['filename'])
            if len(name) > list_width - 4: 
                name = name[:list_width-4] + ".."
            
            if list_item_idx == selected_idx:
                line += rgb_bg(80, 80, 95) + rgb_fg(130, 255, 130) + f"❯  {name:<{list_width-5}} ❮"
            elif list_item_idx == hover_idx:
                line += rgb_bg(*ui_hover_bg) + rgb_fg(*ui_fg) + f"   {name:<{list_width-3}}"
            else:
                line += rgb_bg(*ui_bg) + rgb_fg(*ui_fg) + f"   {name:<{list_width-3}}"
        else:
            line += rgb_bg(*ui_bg) + (" " * list_width)
            
        # --- RIGHT PANEL (Preview) ---
        if r < len(right_lines):
            p_line = right_lines[r]
        else:
            p_line = "  "

        line += rgb_bg(*th_bg) + rgb_fg(*th_fg) + p_line + ERASE_EOL
        frame.append(line)
        
    sys.stdout.write(HOME + "\r\n".join(frame) + RESET)
    sys.stdout.flush()

def read_key():
    ch = sys.stdin.read(1)
    if ch == '\x1b':
        fd = sys.stdin.fileno()
        old_flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, old_flags | os.O_NONBLOCK)
        try:
            seq = sys.stdin.read(2)
            if not seq: 
                return 'esc'
                
            if seq == '[A': return 'up'
            if seq == '[B': return 'down'
            if seq == '[5': sys.stdin.read(1); return 'pgup'
            if seq == '[6': sys.stdin.read(1); return 'pgdown'
            
            if seq == '[<':
                fcntl.fcntl(fd, fcntl.F_SETFL, old_flags)
                mouse_seq = ''
                while True:
                    c = sys.stdin.read(1)
                    mouse_seq += c
                    if c in 'Mm': break
                
                parts = mouse_seq[:-1].split(';')
                cb, cx, cy = int(parts[0]), int(parts[1]), int(parts[2])
                
                if cb == 35: # Fare hareketi (Hover)
                    return ('hover', cx, cy)
                
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
    hover_idx = -1
    last_state = None

    signal.signal(signal.SIGWINCH, handle_resize)

    # Hover için 1003 Modu
    ENABLE_MOUSE = "\033[?1003h\033[?1006h"
    DISABLE_MOUSE = "\033[?1003l\033[?1006l"

    try:
        tty.setraw(fd)
        sys.stdout.write(HIDE + CLEAR + ENABLE_MOUSE) 
        
        last_scroll_time = 0
        
        while True:
            cols, rows = shutil.get_terminal_size()
            max_visible = rows 
            
            if selected_idx < window_start:
                window_start = selected_idx
            elif selected_idx >= window_start + max_visible:
                window_start = selected_idx - max_visible + 1

            current_state = (selected_idx, window_start, hover_idx, cols, rows)
            if current_state != last_state:
                draw_screen(themes, selected_idx, window_start, hover_idx)
                last_state = current_state
            
            try:
                key = read_key()
            except ResizeEvent:
                last_state = None 
                continue 
            
            if key in ('esc', 'q'):
                break
            elif key == 'ignore': 
                continue
                
            if not isinstance(key, tuple):
                hover_idx = -1
                
            if key in ('up', 'k'):
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
                if cx <= 32 and cy >= 1:
                    clicked_idx = window_start + (cy - 1)
                    if 0 <= clicked_idx < len(themes):
                        selected_idx = clicked_idx
                        
            elif isinstance(key, tuple) and key[0] == 'hover':
                _, cx, cy = key
                if cx <= 32 and cy >= 1:
                    h_idx = window_start + (cy - 1)
                    if 0 <= h_idx < len(themes):
                        hover_idx = h_idx
                    else:
                        hover_idx = -1
                else:
                    hover_idx = -1
                
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        sys.stdout.write(DISABLE_MOUSE + SHOW + CLEAR + HOME + RESET)
        sys.stdout.flush()

if __name__ == '__main__':
    main() 
