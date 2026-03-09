# Simple R computations example
# This script demonstrates basic R operations

# Basic arithmetic
a <- 5
b <- 3
sum_ab <- a + b
diff_ab <- a - b
prod_ab <- a * b
div_ab <- a / b

# Vector operations
x <- c(1, 2, 3, 4, 5)
y <- c(10, 20, 30, 40, 50)
z <- x + y

# Mean and standard deviation
mean_x <- mean(x)
sd_x <- sd(x)

# Matrix operations
mat <- matrix(1:9, nrow = 3, ncol = 3)
mat_sum <- sum(mat)
mat_mean <- mean(mat)

# Logical operations
is_positive <- a > 0
all_positive <- all(x > 0)

# String operations
greeting <- "Hello, R!"
