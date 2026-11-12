import re
import sys
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
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
    """Modal dialog: choose format, optionally enter a key, and toggle Gaussian fit."""
    result = {"fmt": None, "key": None, "gauss": False, "ok": False}

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

    # Gaussian fit checkbox
    gauss_var = tk.BooleanVar(value=False)
    tk.Checkbutton(dlg, text="Fit & show Gaussian distribution (σ)", variable=gauss_var
                   ).grid(row=len(FORMATS)+2, column=0, columnspan=2, padx=12, pady=(8, 2), sticky="w")

    # initialise visibility
    _toggle_key(fmt_var, key_entry, key_label)

    def on_ok():
        result["fmt"]   = fmt_var.get()
        result["key"]   = key_entry.get().strip()
        result["gauss"] = gauss_var.get()
        result["ok"]    = True
        dlg.destroy()

    def on_cancel():
        dlg.destroy()

    btn_frame = tk.Frame(dlg)
    btn_frame.grid(row=len(FORMATS)+3, column=0, columnspan=2, pady=12)
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


def gaussian(x, amplitude, mean, sigma):
    """Standard Gaussian function."""
    return amplitude * np.exp(-0.5 * ((x - mean) / sigma) ** 2)


def fit_gaussian(bin_centers, counts):
    """
    Fit a Gaussian to histogram counts.
    Returns (popt, pcov) where popt = [amplitude, mean, sigma],
    or (None, None) if the fit fails.
    """
    # Initial guesses from data moments
    total = counts.sum()
    if total == 0:
        return None, None

    mean0     = np.average(bin_centers, weights=counts)
    sigma0    = np.sqrt(np.average((bin_centers - mean0) ** 2, weights=counts))
    amp0      = counts.max()

    try:
        popt, pcov = curve_fit(
            gaussian, bin_centers, counts,
            p0=[amp0, mean0, max(sigma0, 0.5)],
            maxfev=10_000
        )
        popt[2] = abs(popt[2])   # sigma is always positive
        return popt, pcov
    except RuntimeError:
        return None, None


def plot(values, fmt_name, key, filename, fit_gauss=False):
    arr = np.array(values)
    print(f"{len(arr)} values parsed")

    counts_data, bin_edges = np.histogram(values, bins=range(int(min(values)), int(max(values)) + 2))
    bin_centers = bin_edges[:-1] + 0.5          # centre of each bin

    print(f"max value: {np.max(arr)} ADC code.")

    print(f"most common value: {values[np.argmax(counts_data)]} ADC code.")

    fig, ax = plt.subplots(figsize=(6, 3))
    ax.bar(bin_edges[:-1], counts_data, width=1, align='edge',
           color="tab:blue", alpha=0.7, label="data")

    if fit_gauss:
        popt, pcov = fit_gaussian(bin_centers, counts_data)

        if popt is not None:
            amp, mean, sigma = popt

            # Smooth curve for the fit
            x_fit  = np.linspace(bin_edges[0], bin_edges[-1], 500)
            y_fit  = gaussian(x_fit, amp, mean, sigma)

            # Uncertainty on sigma (1-sigma of the fit parameter itself)
            perr = np.sqrt(np.diag(pcov))
            sigma_err = perr[2]

            ax.plot(x_fit, y_fit, color="tab:orange", linewidth=2,
                    label=f"Gaussian fit\nμ = {mean:.2f}\nσ = {sigma:.2f} ± {sigma_err:.2f}")

            # ±1σ and ±2σ shaded regions
            for n, alpha, lbl in [(2, 0.10, "±2σ"), (1, 0.20, "±1σ")]:
                ax.axvspan(mean - n * sigma, mean + n * sigma,
                           color="tab:orange", alpha=alpha, label=lbl)

            # Vertical lines at ±1σ
            for sign in (-1, 1):
                ax.axvline(mean + sign * sigma, color="tab:orange",
                           linestyle="--", linewidth=1.2, alpha=0.9)

            ax.axvline(mean, color="tab:red", linestyle="-", linewidth=1.5,
                       alpha=0.8, label=f"mean = {mean:.2f}")

            print(f"Gaussian fit:  μ = {mean:.4f},  σ = {sigma:.4f} ± {sigma_err:.4f}")
        else:
            messagebox.showwarning("Fit failed",
                                   "Could not fit a Gaussian to this data.\n"
                                   "The distribution may be too non-Gaussian or have too few points.")
            print("Gaussian fit failed.")

    ax.set_title(f'"{filename}" histogram', fontsize=10)
    ax.set_xlabel("ADC value")
    ax.set_ylabel("count")
    
    #ax.set_xlim(940, 980)


    mean = 955
    conversion_factor = 0.301/0.8056 #from energy to ADC code
    #thorium_238kev_line = mean + 238.6 * conversion_factor
    #thorium_129kev_line = mean + 129 * conversion_factor
    #thorium_84kev_line = mean + 84 * conversion_factor
    #cesium_32kev_line = mean + 32 * conversion_factor

    max_keV = (max(bin_edges) - mean) * (1/conversion_factor)

    print(f"max kev: {max_keV}")

    #cs137_32kev_line = mean + 32 * conversion_factor
    #am241_59kev_line = mean + 59.54 * conversion_factor
    #am241_26kev_line = mean + 26.34 * conversion_factor

    #am241_120kev_line = mean + 120 * conversion_factor

    #ax.axvline(am241_26kev_line, color="tab:orange", linestyle="--", linewidth=1.5, label=f"26keV")
    #ax.axvline(mean, color="tab:red", linestyle="-", linewidth=1.5, label=f"mean baseline")
    #ax.axvline(am241_59kev_line, color="tab:green", linestyle="--", linewidth=1.5, label=f"59keV")
    #ax.axvline(am241_120kev_line, color="tab:green", linestyle="--", linewidth=1.5, label=f"120keV")

    #e110kev_line = mean + 110 * conversion_factor
    #ax.axvline(thorium_129kev_line, color="tab:orange", linestyle="--", linewidth=1.5, label=f"129keV")
    #ax.axvline(thorium_238kev_line, color="tab:green", linestyle="--", linewidth=1.5, label=f"239keV")
    #ax.axvline(thorium_84kev_line, color="tab:blue", linestyle="--", linewidth=1.5, label=f"84keV")

    #ax.axvline(cesium_32kev_line, color="tab:blue", linestyle="--", linewidth=1.5, label=f"84keV")




    ax.set_yscale("log")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(loc="upper right", fontsize=9)
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

    fmt_name  = selection["fmt"]
    key       = selection["key"] if fmt_name in NEEDS_KEY else ""
    fit_gauss = selection["gauss"]

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
    plot(values, fmt_name, key, filename, fit_gauss=fit_gauss)