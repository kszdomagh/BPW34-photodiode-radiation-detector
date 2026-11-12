import re
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

def parse_log(filepath):
    data = []
    with open(filepath, 'r') as f:
        for line in f:
            match = re.search(r'p:\s*(\d+)', line)
            if match:
                data.append(int(match.group(1)))
    return data



def plot(xdata, ydata):
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(xdata, ydata, 'o', linestyle='-', color="tab:red", linewidth=0.8)
    #ax.set_title(f'peak values values for "{filename}" file')
    #ax.set_ylabel("ADC code")
    #ax.set_xlabel(f"n\n")
    plt.tight_layout()
    plt.show()
    

filepath = "serial_data/15-04-2026-cs137-time-all.log" 
samples = parse_log(filepath)
samples_series = pd.Series(samples)
n_vector = np.linspace(0, len(samples)-1, len(samples))

plot(n_vector, samples)

print(f"sample number: {len(samples)}")