# Simple computations in Julia - Wrong Solution
# This has intentional errors for testing

# Initialization of basic variables (correct)
a = 2.0
b = 4.3
x = 0:0.1:1
y = x .+ 1

# Some arithmetic operations - WRONG: sum_1 uses subtraction
v_ax = a .* x
v_by = b .* y
sum_1 = x .- y  # Wrong! Should be x .+ y
sum_2 = v_ax .+ v_by
sub_1 = x .- y
prod_1 = x .* y
quot_1 = x ./ a
quot_2 = x ./ y
pot_1 = x.^a
pot_2 = x.^y

# Roots, exponentials, and logarithm
root_1 = sqrt.(x)
root_2 = x.^(1/3)
expo_1 = exp.(-x)
expo_2 = 10.0.^x
log_1 = log.(y)
log_2 = log10.(y)

# Trigonometric functions - WRONG: trig_1 uses cos instead of sin
trig_1 = cos.(x)  # Wrong! Should be sin.(x)
trig_2 = sin.(x).^2
trig_3 = sin.(x .+ y)
trig_4 = cos.(pi .* x)
