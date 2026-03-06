# Vector Creation in R

# Simple vectors
zero <- rep(0, 8)
one_vec <- rep(1, 7)
five_vec <- rep(5, 6)
empty_vec <- c()
irregular <- c(1, 7, 5, 12, 3)

# Sequences
seq_1 <- 0:5
seq_2 <- seq(0, 5, by = 0.5)
seq_3 <- seq(5, 0, by = -1)
seq_by <- seq(0, 5, length.out = 90)
seq_len <- seq(5, 0, length.out = 80)

# Logarithmic and exponential
log_seq <- 10^seq(-2, 2, length.out = 9)
log_values <- log10(log_seq)
exp_seq <- exp(-2:3)
exp_values <- log(exp_seq)

# Mathematical operations
pow_2 <- 2^(0:10)
log2_pow <- log2(pow_2)
cumsum_vec <- cumsum(1:6)
factorial_vec <- factorial(0:6)
