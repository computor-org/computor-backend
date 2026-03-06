# Functions in Julia
# This is a student template file

# Simple function definition
function add_numbers(a, b)
    return a + b
end

# Function with multiple return values
function minmax(arr)
    return minimum(arr), maximum(arr)
end

# Anonymous function (lambda)
square = x -> x^2

# Function with default argument
function greet(name="World")
    return "Hello, $(name)!"
end

# Recursive function - factorial
function factorial_recursive(n)
    if n <= 1
        return 1
    else
        return n * factorial_recursive(n - 1)
    end
end

# Function with type annotation
function circle_area(r::Float64)::Float64
    return pi * r^2
end

# Test the functions
result_add = add_numbers(3, 5)
result_minmax = minmax([5, 2, 8, 1, 9])
result_square = square(4)
result_greet = greet("Julia")
result_factorial = factorial_recursive(5)
result_area = circle_area(2.0)
