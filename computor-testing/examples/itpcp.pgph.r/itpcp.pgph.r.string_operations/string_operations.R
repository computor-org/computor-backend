# String Operations in R

# Basic strings
greeting <- "Hello, World!"
name <- "R Programming"
str_length <- nchar(greeting)

# String manipulation
upper_str <- toupper("hello")
lower_str <- tolower("HELLO")
concat_str <- paste("Hello", "World", sep = " ")
substr_result <- substr(greeting, 1, 5)

# String search
text <- "The quick brown fox jumps over the lazy dog"
has_pattern <- grepl("fox", text)
pattern_pos <- regexpr("fox", text)[1]
replaced_str <- gsub("fox", "cat", text)

# String splitting
sentence <- "one two three four five"
words <- strsplit(sentence, " ")[[1]]
word_count <- length(words)
