#!/usr/bin/env python3
"""Vigia de estado de input da sessao (XWayland/mutter) para cacar o travamento de selecao de texto.

Amostra a cada 2s e so grita quando algo esta fora do normal, para o log ficar legivel.
NUNCA tenta grab de ponteiro no modo continuo: um grab de microssegundos poderia
quebrar justamente o arrasto do mouse que estamos investigando.

Uso:
  input-watch.py            # vigia continuo (log em ~/.local/state/bananafone/input-watch.log)
  input-watch.py --once     # foto unica do estado atual, inclui teste de grab
"""
import os, sys, time, subprocess
from Xlib import display, X, Xatom

LOG = os.path.expanduser("~/.local/state/bananafone/input-watch.log")
MODS = [(1 << 0, "Shift"), (1 << 1, "Caps"), (1 << 2, "Control"), (1 << 3, "Alt"),
        (1 << 4, "NumLock"), (1 << 5, "Mod3"), (1 << 6, "Super"), (1 << 7, "AltGr"),
        (1 << 8, "BOTAO1"), (1 << 9, "BOTAO2"), (1 << 10, "BOTAO3"), (1 << 11, "BOTAO4"),
        (1 << 12, "BOTAO5")]
NORMAL = 1 << 4          # so NumLock ligado e o estado saudavel
INTERVALO = 2.0
CADA_N_SELECAO = 5       # a cada 5 amostras (10s) checa saude da selecao

def escreve(linha):
    print(linha, flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(linha + "\n")
    except Exception:
        pass

def decodifica(mask):
    return [n for b, n in MODS if mask & b] or ["limpo"]

def descreve_janela(d, w):
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

BASE_OVR = set()   # janelas override-redirect que ja existiam no inicio (mutter: guard window)


def override_redirect_mapeadas(d, root, so_novas=True):
    """Menu Tk postado e uma janela override-redirect mapeada; se vazar, fica aqui."""
    achadas = []
    try:
        for w in root.query_tree().children:
            try:
                a = w.get_attributes()
                if a.override_redirect and a.map_state == X.IsViewable:
                    g = w.get_geometry()
                    if g.width * g.height < 16:
                        continue      # cursores/janelas tecnicas de 1px
                    if so_novas and w.id in BASE_OVR:
                        continue
                    achadas.append(f"0x{w.id:x} {g.width}x{g.height}+{g.x}+{g.y} {descreve_janela(d, w)}")
            except Exception:
                continue
    except Exception:
        pass
    return achadas

def saude_selecao(d):
    """Dono da PRIMARY no lado X e latencia de leitura no lado Wayland."""
    dono = "ninguem"
    try:
        w = d.get_selection_owner(d.intern_atom("PRIMARY"))
        if w and w != X.NONE:
            dono = f"0x{w.id:x} {descreve_janela(d, w)}"
    except Exception:
        pass
    ini = time.time()
    try:
        subprocess.run(["wl-paste", "--primary", "--no-newline"], timeout=2,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ms = int((time.time() - ini) * 1000)
    except subprocess.TimeoutExpired:
        ms = -1     # -1 = pendurou, ponte de selecao travada
    except Exception:
        ms = -2
    return dono, ms

def teclas_presas(d):
    presas = []
    try:
        for i, b in enumerate(d.query_keymap()):
            b = b if isinstance(b, int) else ord(b)
            for bit in range(8):
                if b & (1 << bit):
                    presas.append(str(i * 8 + bit))
    except Exception:
        pass
    return presas

def bananaphone_vivo():
    try:
        out = subprocess.run(["pgrep", "-x", "python3", "-a"], capture_output=True, text=True).stdout
    except Exception:
        out = ""
    for linha in out.splitlines():
        if "bananaphone.py" in linha:
            return linha.split()[0]
    try:
        # o app roda pelo python da venv, cujo comm nao e python3
        out = subprocess.run(["ps", "-eo", "pid=,cmd="], capture_output=True, text=True).stdout
        for linha in out.splitlines():
            if "bananaphone.py" in linha and "input-watch" not in linha:
                return linha.split()[0]
    except Exception:
        pass
    return None

def foto(d, root, checa_selecao):
    p = root.query_pointer()
    mask = p.mask
    presas = teclas_presas(d)
    ovr = override_redirect_mapeadas(d, root, so_novas=True)
    bp = bananaphone_vivo()
    partes = [f"mask=0x{mask:04x}[{'+'.join(decodifica(mask))}]",
              f"ptr={p.root_x},{p.root_y}",
              f"teclas={','.join(presas) if presas else '-'}",
              f"ovr={len(ovr)}",
              f"bp={bp or 'fechado'}"]
    anomalia = (mask & ~NORMAL) & 0x1fff or presas or ovr
    if checa_selecao:
        dono, ms = saude_selecao(d)
        partes.append(f"primary_dono={dono} wl_paste={ms}ms")
        if ms < 0:
            anomalia = True
    linha = " ".join(partes)
    if ovr:
        linha += " | override_redirect: " + " ; ".join(ovr)
    return linha, bool(anomalia)

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
    uma_vez = "--once" in sys.argv
    if uma_vez:
        linha, anomalia = foto(d, root, True)
        escreve(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] FOTO {'ANOMALIA' if anomalia else 'normal'} {linha}")
        r = root.grab_pointer(True, X.NONE, X.GrabModeAsync, X.GrabModeAsync, X.NONE, X.NONE, X.CurrentTime)
        escreve(f"    grab_pointer={'LIVRE' if r == 0 else 'OCUPADO(' + str(r) + ')'}")
        if r == 0:
            d.ungrab_pointer(X.CurrentTime)
        r = root.grab_keyboard(True, X.GrabModeAsync, X.GrabModeAsync, X.CurrentTime)
        escreve(f"    grab_keyboard={'LIVRE' if r == 0 else 'OCUPADO(' + str(r) + ')'}")
        if r == 0:
            d.ungrab_keyboard(X.CurrentTime)
        d.sync()
        return

    escreve(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] === vigia iniciado (pid {os.getpid()}) baseline_ovr={[hex(i) for i in sorted(BASE_OVR)]} ===")
    n = 0
    anterior_bp = None
    ultima_normal = 0.0
    while True:
        try:
            n += 1
            linha, anomalia = foto(d, root, n % CADA_N_SELECAO == 1)
            agora = time.strftime("%H:%M:%S")
            bp_atual = "vivo" if "bp=fechado" not in linha else "fechado"
            if bp_atual != anterior_bp:
                escreve(f"[{agora}] BANANAPHONE {bp_atual.upper()} :: {linha}")
                anterior_bp = bp_atual
            elif anomalia:
                escreve(f"[{agora}] ALERTA {linha}")
            elif time.time() - ultima_normal > 300:
                escreve(f"[{agora}] normal {linha}")
                ultima_normal = time.time()
        except Exception as exc:
            escreve(f"[{time.strftime('%H:%M:%S')}] erro na amostra: {exc}")
        time.sleep(INTERVALO)

if __name__ == "__main__":
    main()
