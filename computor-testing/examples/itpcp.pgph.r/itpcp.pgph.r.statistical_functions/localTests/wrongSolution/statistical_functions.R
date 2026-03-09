# Statistical Functions in R - WRONG SOLUTION
# This script contains intentional errors for testing

# Basic statistics - wrong data
data_vec <- c(2, 4, 6, 8, 10, 12, 14, 16, 18, 20)
data_mean <- 15  # WRONG: should be 11
data_median <- median(data_vec)
data_sd <- sd(data_vec)
data_var <- var(data_vec)

# Range and quantiles - some wrong values
data_min <- min(data_vec)
data_max <- 100  # WRONG: should be 20
data_range <- range(data_vec)
data_quantiles <- quantile(data_vec, probs = c(0.25, 0.5, 0.75))
data_iqr <- IQR(data_vec)

# Correlation and covariance
x_data <- c(1, 2, 3, 4, 5)
y_data <- c(2, 4, 5, 4, 5)
correlation <- 0.5  # WRONG: should be cor(x_data, y_data)
covariance <- cov(x_data, y_data)

# Summary statistics
sorted_data <- sort(data_vec)
unique_count <- length(unique(c(1, 2, 2, 3, 3, 3, 4)))
freq_count <- length(table(c(1, 2, 2, 3, 3, 3, 4)))
