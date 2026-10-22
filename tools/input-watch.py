#!/usr/bin/env python3
"""Session input-state watcher (XWayland/mutter) for hunting the text-selection freeze.

Samples every 2 s and only reports when something is off, so the log stays readable.
NEVER attempts a pointer grab in continuous mode: even a microsecond grab could
break the very mouse drag being investigated.

Usage:
  input-watch.py            # continuous watch (log at ~/.local/state/bananafone/input-watch.log)
  input-watch.py --once     # single snapshot of the current state, includes a grab test
"""
import os, sys, time, subprocess
from Xlib import display, X, Xatom

LOG = os.path.expanduser("~/.local/state/bananafone/input-watch.log")
MODS = [(1 << 0, "Shift"), (1 << 1, "Caps"), (1 << 2, "Control"), (1 << 3, "Alt"),
        (1 << 4, "NumLock"), (1 << 5, "Mod3"), (1 << 6, "Super"), (1 << 7, "AltGr"),
        (1 << 8, "BUTTON1"), (1 << 9, "BUTTON2"), (1 << 10, "BUTTON3"), (1 << 11, "BUTTON4"),
        (1 << 12, "BUTTON5")]
NORMAL = 1 << 4          # only NumLock on is the healthy state
INTERVAL = 2.0
SELECTION_EVERY_N = 5    # every 5 samples (10 s) check selection health

def write_line(line):
    print(line, flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def decode_mask(mask):
    return [n for b, n in MODS if mask & b] or ["clear"]

def describe_window(d, w):
    try:
        cls = w.get_wm_class()
    except Exception:
        cls = None
    pid = None
    try:
        p = w.get_full_property(d.intern_atom("_NET_WM_PID"), Xatom.CARDINAL)
        if p:
            pid = p.value[0]
    except Exception:
        pass
    return f"{cls[1] if cls else '?'}(pid={pid})"

BASE_OVR = set()   # override-redirect windows already present at startup (mutter: guard window)


def mapped_override_redirect(d, root, only_new=True):
    """A posted Tk menu is a mapped override-redirect window; if one leaks, it shows up here."""
    found = []
    try:
        for w in root.query_tree().children:
            try:
                a = w.get_attributes()
                if a.override_redirect and a.map_state == X.IsViewable:
                    g = w.get_geometry()
                    if g.width * g.height < 16:
                        continue      # cursors / 1px technical windows
                    if only_new and w.id in BASE_OVR:
                        continue
                    found.append(f"0x{w.id:x} {g.width}x{g.height}+{g.x}+{g.y} {describe_window(d, w)}")
            except Exception:
                continue
    except Exception:
        pass
    return found

def selection_health(d):
    """PRIMARY owner on the X side and read latency on the Wayland side."""
    owner = "nobody"
    try:
        w = d.get_selection_owner(d.intern_atom("PRIMARY"))
        if w and w != X.NONE:
            owner = f"0x{w.id:x} {describe_window(d, w)}"
    except Exception:
        pass
    start = time.time()
    try:
        subprocess.run(["wl-paste", "--primary", "--no-newline"], timeout=2,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ms = int((time.time() - start) * 1000)
    except subprocess.TimeoutExpired:
        ms = -1     # -1 = hung, selection bridge stuck
    except Exception:
        ms = -2
    return owner, ms

def stuck_keys(d):
    stuck = []
    try:
        for i, b in enumerate(d.query_keymap()):
            b = b if isinstance(b, int) else ord(b)
            for bit in range(8):
                if b & (1 << bit):
                    stuck.append(str(i * 8 + bit))
    except Exception:
        pass
    return stuck

def bananaphone_pid():
    try:
        out = subprocess.run(["pgrep", "-x", "python3", "-a"], capture_output=True, text=True).stdout
    except Exception:
        out = ""
    for line in out.splitlines():
        if "bananaphone.py" in line:
            return line.split()[0]
    try:
        # the app runs on the venv python, whose comm is not python3
        out = subprocess.run(["ps", "-eo", "pid=,cmd="], capture_output=True, text=True).stdout
        for line in out.splitlines():
            if "bananaphone.py" in line and "input-watch" not in line:
                return line.split()[0]
    except Exception:
        pass
    return None

def snapshot(d, root, check_selection):
    p = root.query_pointer()
    mask = p.mask
    stuck = stuck_keys(d)
    ovr = mapped_override_redirect(d, root, only_new=True)
    bp = bananaphone_pid()
    parts = [f"mask=0x{mask:04x}[{'+'.join(decode_mask(mask))}]",
             f"ptr={p.root_x},{p.root_y}",
             f"keys={','.join(stuck) if stuck else '-'}",
             f"ovr={len(ovr)}",
             f"bp={bp or 'closed'}"]
    anomaly = (mask & ~NORMAL) & 0x1fff or stuck or ovr
    if check_selection:
        owner, ms = selection_health(d)
        parts.append(f"primary_owner={owner} wl_paste={ms}ms")
        if ms < 0:
            anomaly = True
    line = " ".join(parts)
    if ovr:
        line += " | override_redirect: " + " ; ".join(ovr)
    return line, bool(anomaly)

def main():
    d = display.Display()
    root = d.screen().root
    global BASE_OVR
    for w in root.query_tree().children:
        try:
            a = w.get_attributes()
            if a.override_redirect and a.map_state == X.IsViewable:
                BASE_OVR.add(w.id)
        except Exception:
            continue
    once = "--once" in sys.argv
    if once:
        line, anomaly = snapshot(d, root, True)
        write_line(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] SNAPSHOT {'ANOMALY' if anomaly else 'normal'} {line}")
        r = root.grab_pointer(True, X.NONE, X.GrabModeAsync, X.GrabModeAsync, X.NONE, X.NONE, X.CurrentTime)
        write_line(f"    grab_pointer={'FREE' if r == 0 else 'BUSY(' + str(r) + ')'}")
        if r == 0:
            d.ungrab_pointer(X.CurrentTime)
        r = root.grab_keyboard(True, X.GrabModeAsync, X.GrabModeAsync, X.CurrentTime)
        write_line(f"    grab_keyboard={'FREE' if r == 0 else 'BUSY(' + str(r) + ')'}")
        if r == 0:
            d.ungrab_keyboard(X.CurrentTime)
        d.sync()
        return

    write_line(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] === watcher started (pid {os.getpid()}) baseline_ovr={[hex(i) for i in sorted(BASE_OVR)]} ===")
    n = 0
    previous_bp = None
    last_normal = 0.0
    while True:
        try:
            n += 1
            line, anomaly = snapshot(d, root, n % SELECTION_EVERY_N == 1)
            now = time.strftime("%H:%M:%S")
            bp_state = "running" if "bp=closed" not in line else "closed"
            if bp_state != previous_bp:
                write_line(f"[{now}] BANANAPHONE {bp_state.upper()} :: {line}")
                previous_bp = bp_state
            elif anomaly:
                write_line(f"[{now}] ALERT {line}")
            elif time.time() - last_normal > 300:
                write_line(f"[{now}] normal {line}")
                last_normal = time.time()
        except Exception as exc:
            write_line(f"[{time.strftime('%H:%M:%S')}] sample error: {exc}")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
