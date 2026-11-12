import re
import sys
import numpy as np
import matplotlib.pyplot as plt
from tkinter import filedialog, Tk, simpledialog, messagebox
import tkinter as tk

# ── format registry ──────────────────────────────────────────────────────────

FORMATS = {
    "prefix: value  (e.g.  p: 1234)":          lambda key: re.compile(rf"^{re.escape(key)}:\s*([\d.]+)", re.MULTILINE),
    "bare numbers  (e.g.  1234)":               lambda _:   re.compile(r"^([\d.]+)", re.MULTILINE),
}

NEEDS_KEY = {
    "prefix: value  (e.g.  p: 1234)",
}

# ── GUI helpers ───────────────────────────────────────────────────────────────

def pick_format_and_key(root):
    """Modal dialog: choose format, optionally enter a key."""
    result = {"fmt": None, "key": None, "ok": False}

    dlg = tk.Toplevel(root)
    dlg.title("Select value format")
    dlg.resizable(False, False)
    dlg.grab_set()

    tk.Label(dlg, text="Format:", anchor="w").grid(row=0, column=0, columnspan=2,
                                                    padx=12, pady=(12, 2), sticky="w")

    fmt_var = tk.StringVar(value=list(FORMATS)[0])
    for i, name in enumerate(FORMATS):
        tk.Radiobutton(dlg, text=name, variable=fmt_var, value=name,
                       command=lambda: _toggle_key(fmt_var, key_entry, key_label)
                       ).grid(row=i+1, column=0, columnspan=2, padx=20, sticky="w")

    key_label = tk.Label(dlg, text="Key / prefix:", anchor="w")
    key_label.grid(row=len(FORMATS)+1, column=0, padx=12, pady=(10, 2), sticky="w")
    key_entry = tk.Entry(dlg, width=20)
    key_entry.insert(0, "p")
    key_entry.grid(row=len(FORMATS)+1, column=1, padx=12, pady=(10, 2), sticky="w")

    # initialise visibility
    _toggle_key(fmt_var, key_entry, key_label)

    def on_ok():
        result["fmt"] = fmt_var.get()
        result["key"] = key_entry.get().strip()
        result["ok"] = True
        dlg.destroy()

    def on_cancel():
        dlg.destroy()

    btn_frame = tk.Frame(dlg)
    btn_frame.grid(row=len(FORMATS)+2, column=0, columnspan=2, pady=12)
    tk.Button(btn_frame, text="OK",     width=10, command=on_ok    ).pack(side="left",  padx=6)
    tk.Button(btn_frame, text="Cancel", width=10, command=on_cancel).pack(side="right", padx=6)

    dlg.wait_window()
    return result


def _toggle_key(fmt_var, entry, label):
    if fmt_var.get() in NEEDS_KEY:
        label.config(state="normal")
        entry.config(state="normal")
    else:
        label.config(state="disabled")
        entry.config(state="disabled")


def pick_file(root):
    path = filedialog.askopenfilename(
        parent=root,
        title="Select log file",
        filetypes=[("Log files", "*.log *.txt"), ("All files", "*.*")]
    )
    return path

# ── core logic ────────────────────────────────────────────────────────────────

def parse(filepath, fmt_name, key=""):
    pattern = FORMATS[fmt_name](key)
    with open(filepath, "r", errors="ignore") as f:
        return [float(v) for v in pattern.findall(f.read())]
    

def extract_peaks(signal, threshold):
    peaks = []
    in_pulse = False
    current_max = -np.inf

    for v in signal:
        if v > threshold:
            in_pulse = True
            if v > current_max:
                current_max = v
        else:
            if in_pulse:
                peaks.append(current_max)
                current_max = -np.inf
                in_pulse = False

    return peaks


def plot(values, fmt_name, key, filename):
    arr = np.array(values)
    print(f"{len(arr)} raw samples")

    # --- pulse detection ---
    threshold = 966
    peaks = extract_peaks(arr, threshold)

    peaks = np.array(peaks)
    print(f"{len(peaks)} pulses detected")

    if len(peaks) == 0:
        print("No pulses found — adjust threshold")
        return

    # --- spectrum (histogram of peaks) ---
    fig, ax = plt.subplots(figsize=(5, 5))

    vals, counts = np.unique(peaks.astype(int), return_counts=True)
    ax.bar(vals, counts, color='tab:green', align='center')
    #ax.set_yscale("log")
    #ax.set_ylim(0, 100)
    #ax.set_xlim(960, 1000)

    mean = 957
    conversion_factor = 0.301/0.8056
    cs137_32kev_line = mean + 32 * conversion_factor
    am241_59kev_line = mean + 59.54 * conversion_factor
    am241_26kev_line = mean + 26.34 * conversion_factor
    #ax.axvline(am241_26kev_line, color="tab:orange", linestyle="--", linewidth=1.5, label=f"26keV")
    #ax.axvline(am241_59kev_line, color="tab:green", linestyle="--", linewidth=1.5, label=f"59keV")

    title_parts = [f'"{filename}" spectrum']
    if key:
        title_parts.append(f'key: {key}')
    ax.set_title(" | ".join(title_parts))

    ax.set_xlabel("Energy [keV]")
    ax.set_ylabel("counts")
    ax.grid(alpha=0.3)
    ax.legend()

    plt.tight_layout()
    plt.show()

# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = Tk()
    root.withdraw()

    selection = pick_format_and_key(root)
    if not selection["ok"]:
        print("Cancelled.")
        root.destroy()
        sys.exit(0)

    fmt_name = selection["fmt"]
    key      = selection["key"] if fmt_name in NEEDS_KEY else ""

    filepath = pick_file(root)
    root.destroy()

    if not filepath:
        print("No file selected.")
        sys.exit(0)

    values = parse(filepath, fmt_name, key)

    if not values:
        hint = f' with key "{key}"' if key else ""
        print(f'No values found using format "{fmt_name}"{hint}.')
        sys.exit(1)

    filename = filepath.replace("\\", "/").split("/")[-1]
    plot(values, fmt_name, key, filename)