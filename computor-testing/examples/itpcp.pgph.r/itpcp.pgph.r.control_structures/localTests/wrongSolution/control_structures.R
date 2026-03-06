# Control Structures in R - WRONG SOLUTION
# This script contains intentional errors for testing

# For loop - sum of 1 to 10 - WRONG range
sum_for <- 0
for (i in 1:8) {  # WRONG: should be 1:10
  sum_for <- sum_for + i
}

# For loop - squares
squares_for <- c()
for (i in 1:5) {
  squares_for <- c(squares_for, i^2)
}

# For loop - factorial - WRONG calculation
factorial_for <- 1
for (i in 1:4) {  # WRONG: should be 1:5
  factorial_for <- factorial_for * i
}

# While loop - sum until exceeds 50
sum_while <- 0
i <- 1
while (sum_while <= 50) {
  sum_while <- sum_while + i
  i <- i + 1
}

# While loop - count iterations
count_while <- 0
n <- 1024
while (n > 1) {
  n <- n / 2
  count_while <- count_while + 1
}

# Conditionals - grade classification - WRONG thresholds
get_grade <- function(score) {
  if (score >= 90) {
    return("A")
  } else if (score >= 80) {
    return("B")
  } else if (score >= 70) {
    return("C")
  } else if (score >= 60) {
    return("D")
  } else {
    return("F")
  }
}

grade_A <- get_grade(95)
grade_B <- "C"  # WRONG: should be "B"
grade_F <- get_grade(45)

# Absolute value using conditional
x <- -5
if (x < 0) {
  abs_value <- -x
} else {
  abs_value <- x
}

# Vectorized operations with ifelse - WRONG labels
numbers <- c(-3, -1, 0, 2, 5)
vec_ifelse <- ifelse(numbers >= 0, "pos", "neg")  # WRONG: should be "positive"/"negative"

# which() for finding indices
data <- c(10, 25, 30, 15, 40, 5)
vec_which <- which(data > 20)

# Filtering with logical indexing
vec_filter <- data[data > 15]
