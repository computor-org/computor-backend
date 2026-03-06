# ChatGPT solution

import numpy as np
import matplotlib.pyplot as plt

def gradient_field(X, Y):
    """
    Berechnet das Gradientenfeld für das Skalarfeld V(r) = r^2.
    """
    R = np.sqrt(X**2 + Y**2)
    grad_X, grad_Y = np.gradient(R**2, axis=(0, 1))
    return grad_X, grad_Y

def plot_gradient_and_transformed_fields():
    # 1. Erzeugen des Gitters von x- und y-Werten
    N = 10
    x = np.linspace(-2, 2, N)
    y = np.linspace(-2, 2, N)
    X, Y = np.meshgrid(x, y)
    
    # 2. Berechnen des Gradientenfeldes
    grad_X, grad_Y = gradient_field(X, Y)
    
    # 3. Plotten des Gradientenfeldes
    fig, axs = plt.subplots(1, 2, figsize=(14, 6))
    
    # Normierung der Vektoren
    norm = np.sqrt(grad_X**2 + grad_Y**2)
    norm[norm == 0] = 1  # Vermeidung von Division durch Null
    grad_X /= norm
    grad_Y /= norm
    
    # Gradientenfeld plotten
    c = axs[0].quiver(X, Y, grad_X, grad_Y, norm, cmap='viridis')
    axs[0].set_title('Gradientenfeld')
    axs[0].set_xlabel('x')
    axs[0].set_ylabel('y')
    fig.colorbar(c, ax=axs[0])
    
    # Basisvektoren plotten
    axs[0].quiver(0, 0, -1, 1, angles='xy', scale_units='xy', scale=1, color='r', label='v1 = [-1, 1]')
    axs[0].quiver(0, 0, 1, 1, angles='xy', scale_units='xy', scale=1, color='b', label='v2 = [1, 1]')
    axs[0].legend()
    
    # 4. Lineare Transformation
    A = np.array([[3, 1], [0, 2]])
    grad_transformed = np.dot(A, np.vstack([grad_X.flatten(), grad_Y.flatten()])).reshape(2, N, N)
    grad_X_trans, grad_Y_trans = grad_transformed
    
    # 5. Plotten des transformierten Gradientenfeldes
    norm_trans = np.sqrt(grad_X_trans**2 + grad_Y_trans**2)
    norm_trans[norm_trans == 0] = 1
    grad_X_trans /= norm_trans
    grad_Y_trans /= norm_trans
    
    # Transformiertes Gradientenfeld plotten
    c = axs[1].quiver(X, Y, grad_X_trans, grad_Y_trans, norm_trans, cmap='viridis')
    axs[1].set_title('Transformiertes Gradientenfeld')
    axs[1].set_xlabel('x')
    axs[1].set_ylabel('y')
    fig.colorbar(c, ax=axs[1])
    
    # Transformierte Basisvektoren plotten
    v1 = np.array([-1, 1])
    v2 = np.array([1, 1])
    v1_trans = A @ v1
    v2_trans = A @ v2
    axs[1].quiver(0, 0, v1_trans[0], v1_trans[1], angles='xy', scale_units='xy', scale=1, color='r', label='v1_trans')
    axs[1].quiver(0, 0, v2_trans[0], v2_trans[1], angles='xy', scale_units='xy', scale=1, color='b', label='v2_trans')
    
    # Eigenvektoren der Transformationsmatrix
    eigvals, eigvecs = np.linalg.eig(A)
    for eigvec in eigvecs.T:
        axs[1].quiver(0, 0, eigvec[0], eigvec[1], angles='xy', scale_units='xy', scale=1, color='g', linestyle='--', label='Eigenvektoren')
    
    axs[1].legend()
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    plot_gradient_and_transformed_fields()
