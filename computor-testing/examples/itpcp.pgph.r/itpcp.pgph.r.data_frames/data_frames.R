# Data Frames in R

# Data frame creation
df <- data.frame(
  name = c("Alice", "Bob", "Charlie", "Diana"),
  age = c(25, 30, 35, 28),
  score = c(85.5, 92.0, 78.5, 88.0)
)
df_nrow <- nrow(df)
df_ncol <- ncol(df)
col_names <- names(df)

# Data frame access
first_col <- df$name
first_row <- df[1, ]
single_value <- df[2, "score"]

# Data frame operations
filtered_df <- df[df$age > 27, ]
sorted_df <- df[order(df$score, decreasing = TRUE), ]
col_mean <- mean(df$score)
