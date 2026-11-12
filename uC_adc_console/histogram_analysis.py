import re
import sys
import numpy as np
import matplotlib.pyplot as plt
from tkinter import filedialog, Tk, simpledialog, messagebox
import tkinter as tk

# ── format registry ──────────────────────────────────────────────────────────

FORMATS = {
    "prefix: value  (e.g.  p: 1234)":         lambda key: re.compile(rf"^{re.escape(key)}:\s*([\d.]+)", re.MULTILINE),
    "bare numbers  (e.g.  1234)":               lambda _:   re.compile(r"^([\d.]+)", re.MULTILINE),
}

NEEDS_KEY = {"prefix: value  (e.g.  p: 1234)"}

# ── GUI helpers ───────────────────────────────────────────────────────────────

def pick_format_and_key(root):
    result = {"fmt": None, "key": None, "ok": False}
    dlg = tk.Toplevel(root)
    dlg.title("Select Pulse Format")
    dlg.grab_set()

    tk.Label(dlg, text="Format:", anchor="w").grid(row=0, column=0, columnspan=2, padx=12, pady=(12, 2))
    
    fmt_var = tk.StringVar(value=list(FORMATS)[0])
    for i, name in enumerate(FORMATS):
        tk.Radiobutton(dlg, text=name, variable=fmt_var, value=name).grid(row=i+1, column=0, columnspan=2, padx=20, sticky="w")

    key_label = tk.Label(dlg, text="Key / prefix:")
    key_label.grid(row=len(FORMATS)+1, column=0, padx=12, pady=10)
    key_entry = tk.Entry(dlg, width=15); key_entry.insert(0, "p")
    key_entry.grid(row=len(FORMATS)+1, column=1, padx=12)

    def on_ok():
        result.update({"fmt": fmt_var.get(), "key": key_entry.get().strip(), "ok": True})
        dlg.destroy()

    tk.Button(dlg, text="Analyze File", command=on_ok, width=15).grid(row=len(FORMATS)+2, column=0, columnspan=2, pady=12)
    dlg.wait_window()
    return result

# ── core logic ────────────────────────────────────────────────────────────────

def parse_data(filepath, fmt_name, key=""):
    pattern = FORMATS[fmt_name](key)
    with open(filepath, "r", errors="ignore") as f:
        return [float(v) for v in pattern.findall(f.read())]

def plot_analysis(values, filename, el=None, eu=None):
    arr = np.array(values)
    indices = np.arange(len(arr))
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    
    # Plot 1: Pulse Transient (Pulse-Height Analyzer View)
    ax1.plot(indices, arr, color='tab:blue', alpha=0.6, label="Raw Pulses")
    if el is not None and eu is not None:
        ax1.axhline(y=el, color='green', linestyle='--', label=f'Lower Level ($E_L$)')
        ax1.axhline(y=eu, color='red', linestyle='--', label=f'Upper Level ($E_U$)')
        
        # Highlight pulses that fall within the window (Anti-coincidence logic)
        mask = (arr >= el) & (arr <= eu)
        ax1.scatter(indices[mask], arr[mask], color='purple', s=10, label="Accepted Pulses", zorder=3)

    ax1.set_title(f"Pulse-Height Analysis: {filename}")
    ax1.set_ylabel("ADC Value / Energy")
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)

    # Plot 2: Gamma Spectrum (Histogram View)
    ax2.hist(arr, bins=100, histtype='stepfilled', color='tab:red', alpha=0.7)
    ax2.set_title("Gamma Spectrum")
    ax2.set_xlabel("Energy (Channel)")
    ax2.set_ylabel("Counts")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = Tk()
    root.withdraw()

    selection = pick_format_and_key(root)
    if not selection["ok"]: sys.exit(0)

    filepath = filedialog.askopenfilename(title="Select Log File")
    if not filepath: sys.exit(0)

    raw_values = parse_data(filepath, selection["fmt"], selection["key"])
    
    if raw_values:
        # Prompt for discriminator levels based on your image diagram
        el = simpledialog.askfloat("Discriminator", "Set Lower Level (EL):", initialvalue=min(raw_values))
        eu = simpledialog.askfloat("Discriminator", "Set Upper Level (EU):", initialvalue=max(raw_values))
        
        fname = filepath.split("/")[-1]
        plot_analysis(raw_values, fname, el, eu)
    else:
        messagebox.showerror("Error", "No valid numerical data found in file.")
    
    root.destroy()