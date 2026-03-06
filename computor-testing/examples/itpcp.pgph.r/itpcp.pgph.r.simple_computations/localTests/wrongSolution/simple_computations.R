# Simple R computations example - WRONG SOLUTION
# This script contains intentional errors for testing

# Basic arithmetic - some wrong values
a <- 5
b <- 3
sum_ab <- a - b  # WRONG: should be a + b
diff_ab <- a - b
prod_ab <- a * b
div_ab <- a / b

# Vector operations - wrong vector
x <- c(1, 2, 3, 4, 5)
y <- c(10, 20, 30, 40, 50)
z <- x * y  # WRONG: should be x + y

# Mean and standard deviation
mean_x <- mean(x)
sd_x <- sd(x)

# Matrix operations - wrong calculation
mat <- matrix(1:9, nrow = 3, ncol = 3)
mat_sum <- sum(mat)
mat_mean <- 10.0  # WRONG: should be 5.0

# Logical operations
is_positive <- a > 0
all_positive <- all(x > 0)

# String operations - wrong string
greeting <- "Hello, Python!"  # WRONG: should be "Hello, R!"
