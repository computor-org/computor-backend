# Functions in R

# Basic function definitions
square <- function(x) {
  return(x^2)
}

cube <- function(x) {
  return(x^3)
}

add <- function(a, b) {
  return(a + b)
}

# Test basic functions
square_result <- square(5)
cube_result <- cube(3)
add_result <- add(3, 4)

# Function with default arguments
greet <- function(name = "World") {
  return(paste("Hello, ", name, "!", sep = ""))
}

greet_default <- greet()
greet_custom <- greet("Alice")

# Recursive factorial
factorial_func <- function(n) {
  if (n <= 1) return(1)
  return(n * factorial_func(n - 1))
}

factorial_result <- factorial_func(5)

# Fibonacci sequence
fibonacci <- function(n) {
  if (n <= 2) return(1)
  fib <- c(1, 1)
  for (i in 3:n) {
    fib <- c(fib, fib[i-1] + fib[i-2])
  }
  return(fib)
}

fibonacci_result <- fibonacci(10)

# Prime number check
is_prime <- function(n) {
  if (n < 2) return(FALSE)
  if (n == 2) return(TRUE)
  if (n %% 2 == 0) return(FALSE)
  if (n < 9) return(TRUE)  # 3, 5, 7 are prime
  for (i in seq(3, sqrt(n), by = 2)) {
    if (n %% i == 0) return(FALSE)
  }
  return(TRUE)
}

is_prime_7 <- is_prime(7)
is_prime_8 <- is_prime(8)

# Vector norm function
calc_norm <- function(v) {
  return(sqrt(sum(v^2)))
}

normalize <- function(v) {
  return(v / calc_norm(v))
}

test_vec <- c(3, 4)
vec_norm <- calc_norm(test_vec)
vec_normalized <- normalize(test_vec)
