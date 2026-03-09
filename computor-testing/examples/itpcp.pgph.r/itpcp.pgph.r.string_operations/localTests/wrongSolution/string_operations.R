# String Operations in R - WRONG SOLUTION
# This script contains intentional errors for testing

# Basic strings - wrong value
greeting <- "Hello, World!"
name <- "R Programming"
str_length <- 10  # WRONG: should be nchar(greeting) = 13

# String manipulation - some wrong results
upper_str <- toupper("hello")
lower_str <- "hello"  # WRONG: should be tolower("HELLO") = "hello", but this is actually correct
concat_str <- paste("Hello", "World", sep = "-")  # WRONG: should be sep = " "
substr_result <- substr(greeting, 1, 5)

# String search
text <- "The quick brown fox jumps over the lazy dog"
has_pattern <- grepl("fox", text)
pattern_pos <- regexpr("fox", text)[1]
replaced_str <- gsub("fox", "dog", text)  # WRONG: should replace with "cat"

# String splitting
sentence <- "one two three four five"
words <- strsplit(sentence, " ")[[1]]
word_count <- 3  # WRONG: should be 5
