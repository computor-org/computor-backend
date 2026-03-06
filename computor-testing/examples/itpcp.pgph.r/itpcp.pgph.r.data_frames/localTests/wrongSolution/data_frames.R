# Data Frames in R - WRONG SOLUTION
# This script contains intentional errors for testing

# Data frame creation - wrong data
df <- data.frame(
  name = c("Alice", "Bob", "Charlie"),  # WRONG: missing "Diana"
  age = c(25, 30, 35),
  score = c(85.5, 92.0, 78.5)
)
df_nrow <- nrow(df)
df_ncol <- ncol(df)
col_names <- names(df)

# Data frame access
first_col <- df$name
first_row <- df[1, ]
single_value <- 100  # WRONG: should be df[2, "score"] = 92.0

# Data frame operations - wrong filter
filtered_df <- df[df$age > 30, ]  # WRONG: should be > 27
sorted_df <- df[order(df$score, decreasing = TRUE), ]
col_mean <- mean(df$score)
