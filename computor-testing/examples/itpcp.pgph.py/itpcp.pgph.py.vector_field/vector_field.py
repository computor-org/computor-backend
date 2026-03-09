import numpy as np
import matplotlib.pyplot as plt


# Define the gradient of the function
def gradient_field(x, y):
    dx = 2 * x
    dy = 2 * y
    return dx, dy


number_of_points = 20

# Base vectors of the grid
origin = np.zeros(2)
base = np.array([[1, 0], [0, 1]])

v1 = np.array([[-1], [1]])
v2 = np.array([[1], [1]])

# Generate grid points
x = np.linspace(-4, 4, number_of_points)
y = np.linspace(-4, 4, number_of_points)
X, Y = np.meshgrid(x, y)

# Compute gradient at each point
DX, DY = gradient_field(X, Y)
magnitude = np.sqrt(DX**2 + DY**2)


# Define transformation matrix
transformation_matrix = np.array([[3, 1], [0, 2]])
# transformation_matrix = np.array([[1, -1], [1, 1]])

print(transformation_matrix)

# Apply linear transformation
transformed_vectors = transformation_matrix @ np.vstack([DX.flatten(), DY.flatten()])

# Reshape transformed vectors back to original shape
transformed_DX = transformed_vectors[0, :].reshape(X.shape)
transformed_DY = transformed_vectors[1, :].reshape(Y.shape)

# magnitude_transformed = np.sqrt(transformed_DX**2 + transformed_DY**2)
magnitude_transformed = np.linalg.norm(transformed_vectors, axis=0).reshape(X.shape)

transformed_base = transformation_matrix @ base
v1_trans = transformation_matrix @ v1
v2_trans = transformation_matrix @ v2


# Compute eigenvectors and eigenvalues
eigenvalue, eigenvector = np.linalg.eig(transformation_matrix)
print(f"Eigenvalues: {eigenvalue} \n Eigenvectors: {eigenvector}")


fig = plt.figure(figsize=(12, 6))
axes = fig.add_subplot(1, 2, 1)
axes.quiver(
    origin,
    origin,
    base[:, 0],
    base[:, 1],
    color="b",
    scale=1,
    scale_units="xy",
    angles="xy",
    label="Base Vectors",
)
axes.quiver(
    origin,
    origin,
    v1[0],
    v1[1],
    color="g",
    scale=1,
    scale_units="xy",
    angles="xy",
    label="v1",
)
axes.quiver(
    origin,
    origin,
    v2[0],
    v2[1],
    color="r",
    scale=1,
    scale_units="xy",
    angles="xy",
    label="v2",
)

vf = axes.quiver(
    X,
    Y,
    DX / magnitude,
    DY / magnitude,
    magnitude,
    cmap="plasma",
    # scale=None,
    # cmap="viridis",
)
axes.set_xlabel("X", fontsize=12)
axes.set_ylabel("Y", fontsize=12)
axes.set_title("Original Gradient Field", fontsize=12)
axes.legend(loc="lower left", fontsize=12)
axes.grid()

# Plot the transformed gradient field
axes = fig.add_subplot(1, 2, 2)
axes.quiver(
    origin,
    origin,
    transformed_base[0, 0],
    transformed_base[1, 0],
    color="b",
    scale=1,
    scale_units="xy",
    angles="xy",
)

axes.quiver(
    origin,
    origin,
    transformed_base[0, 1],
    transformed_base[1, 1],
    color="b",
    scale=1,
    scale_units="xy",
    angles="xy",
    label="Transformed Base Vectors",
)


colors = ["purple", "orange"]

axes.quiver(
    origin,
    origin,
    v1_trans[0],
    v1_trans[1],
    color="g",
    scale=1,
    scale_units="xy",
    angles="xy",
    label="v1",
)
axes.quiver(
    origin,
    origin,
    v2_trans[0],
    v2_trans[1],
    color="r",
    scale=1,
    scale_units="xy",
    angles="xy",
    label="v2",
)

# Plot each eigenvector with its respective color and label
for i in range(len(eigenvalue)):
    axes.quiver(
        origin,
        origin,
        eigenvector[0, i],
        eigenvector[1, i],
        color=colors[i],
        scale=1,
        scale_units="xy",
        angles="xy",
        label=f"Eigenvector {i+1} with Eigenvalue = {eigenvalue[i]:.1f}",
    )
t_vf = axes.quiver(
    X,
    Y,
    transformed_DX / magnitude_transformed,
    transformed_DY / magnitude_transformed,
    magnitude_transformed,
    cmap="plasma",
    # scale=None,
    # scale_units="xy"
)
axes.set_xlabel("X", fontsize=12)
axes.set_ylabel("Y", fontsize=12)
axes.set_title("Transformed Gradient Field", fontsize=12)
axes.legend(loc="lower left", fontsize=12)
axes.grid()

# plt.savefig("gradient_field.png")
# plt.savefig("notes/mediaFiles/gradient_field.png")
plt.show()
