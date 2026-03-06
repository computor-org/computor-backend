# Matrix Operations in R

# Matrix creation
mat_zeros <- matrix(0, nrow = 3, ncol = 4)
mat_ones <- matrix(1, nrow = 3, ncol = 3)
mat_identity <- diag(4)
mat_diag <- diag(c(1, 2, 3, 4))
mat_custom <- matrix(1:12, nrow = 3, ncol = 4, byrow = TRUE)

# Matrix properties
mat_nrow <- nrow(mat_custom)
mat_ncol <- ncol(mat_custom)
mat_dim <- dim(mat_custom)
mat_sum <- sum(mat_custom)
mat_mean <- mean(mat_custom)

# Matrix operations
mat_transpose <- t(mat_custom)
A <- matrix(c(1, 2, 3, 4), nrow = 2)
B <- matrix(c(5, 6, 7, 8), nrow = 2)
mat_product <- A %*% B
mat_elementwise <- A * B
row_sums <- rowSums(mat_custom)
col_sums <- colSums(mat_custom)

# Linear algebra
M <- matrix(c(4, 2, 7, 6), nrow = 2)
mat_det <- det(M)
mat_inv <- solve(M)
b <- c(1, 2)
linear_solve <- solve(M, b)
