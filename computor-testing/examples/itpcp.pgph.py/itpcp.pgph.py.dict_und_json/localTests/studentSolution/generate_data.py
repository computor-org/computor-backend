import json
import numpy as np
from datetime import datetime

# Read data from json file
data_filename = "data_file.json"
with open(data_filename, "r") as fp:
    data = json.load(fp)

# data is a dict
print(data.keys())

# Extract configuration values

data["results"] = {}

config = data["sim_config"]
res = data["results"]

# Perform some computations
for sim_name, sim in config.items():
    mu = float(sim["mu"])
    sig = float(sim["sig"])
    size = sim["size"]

    res_array = mu +  np.random.randn(*size)  # np.random.randn(size[0], size[1])
    res[sim_name] = res_array.tolist()

# Add metadata
data["metadata"] = {
    "date": datetime.now().strftime("%Y-%m-%d"),
    "time": datetime.now().strftime("%H.%M"),
}

# Store the results in the dict and save to another file
new_filename = "results.json"

with open(new_filename, "w") as fp:
    json.dump(data, fp, indent=4)



