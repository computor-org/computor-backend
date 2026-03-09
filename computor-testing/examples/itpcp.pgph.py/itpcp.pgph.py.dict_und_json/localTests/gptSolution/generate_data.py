# ChatGPT solution

import json
import numpy as np
from datetime import datetime

# Read the JSON configuration file
with open('data_file.json', 'r') as file:
    data = json.load(file)

# Extract simulation configuration
sim_config = data['sim_config']

# Initialize results dictionary
results = {}

# Generate data for each simulation configuration
for sim_name, config in sim_config.items():
    mu = config['mu']
    sig = config['sig']
    size = config['size']
    
    # Generate normally distributed random numbers
    results[sim_name] = np.random.normal(mu, sig, size).tolist()

# Add metadata
metadata = {
    'date': datetime.now().strftime('%Y-%m-%d'),
    'time': datetime.now().strftime('%H:%M')
}

# Combine results with metadata
data['results'] = results
data['metadata'] = metadata

# Write the updated dictionary to a JSON file
with open('results.json', 'w') as file:
    json.dump(data, file, indent=4)
