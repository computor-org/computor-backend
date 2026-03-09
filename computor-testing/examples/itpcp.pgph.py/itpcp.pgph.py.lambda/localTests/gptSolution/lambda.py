# ChatGPT solution

import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import simpson

# 1. Lambda function to add two numbers
adder = lambda x, y: x + y

# 2. Sorting Lists Using Lambda Functions
data = [(2, 3), (12, 3), (-4, 5), (6, -7), (8, 9), (-3, 11)]
sorted_y = sorted(data, key=lambda xy: xy[1])
sorted_r = sorted(data, key=lambda xy: (xy[0]**2 + xy[1]**2)**0.5)

# 3. Filtering Even Numbers Using Lambda Functions
l = [7, 2, 3, 12, 6, 13, 4]
evens = list(filter(lambda x: x % 2 == 0, l))

# 4. Function Returning a Lambda Function
def calc_multiple(n):
    return lambda x: x * n

# Example usage of calc_multiple
doubler = calc_multiple(2)
print(doubler(6))  # Output: 12

# 5. Analyzing Periodic Signals

# Parameters
U_0 = 230 * np.sqrt(2)
f = 50
T = 1 / f

# Generate time vector
t = np.linspace(0, T, 500)

# Signal Functions
f_sin = lambda t: U_0 * np.sin(2 * np.pi * f * t)
f_abssin = lambda t: np.abs(U_0 * np.sin(2 * np.pi * f * t))
f_square = lambda t: U_0 * np.sign(np.sin(2 * np.pi * f * t))
f_saw = lambda t: U_0 * (2 * (t / T - np.floor(t / T + 0.5)))

# List of functions
signals = [f_sin, f_abssin, f_square, f_saw]
names = ['Sinusoidal', 'Absolute Sinusoidal', 'Square', 'Sawtooth']
U_mean = []
U_eff = []

# Calculate Mean and Effective Values
for signal in signals:
    U = signal(t)
    U_mean.append(simpson(U, t) / T)
    U_eff.append(np.sqrt(simpson(U**2, t) / T))

# Plotting
fig, axs = plt.subplots(4, 1, figsize=(10, 12), sharex=True)

for i, (signal, name) in enumerate(zip(signals, names)):
    U = signal(t)
    axs[i].plot(t, U, label=name)
    axs[i].axhline(y=U_mean[i], color='r', linestyle='--', label=f'Mean: {U_mean[i]:.2f}')
    axs[i].axhline(y=U_eff[i], color='g', linestyle='--', label=f'Effective Value: {U_eff[i]:.2f}')
    axs[i].set_ylabel('Amplitude')
