# Vector operations in Julia - Correct Solution

# Vector creation
vec1 = [1, 2, 3, 4, 5]
vec2 = collect(1:5)
vec3 = range(0, 10, length=11)
vec4 = zeros(5)
vec5 = ones(5)

# Vector operations
vec_sum = sum(vec1)
vec_prod = prod(vec1)
vec_mean = sum(vec1) / length(vec1)
vec_max = maximum(vec1)
vec_min = minimum(vec1)
vec_len = length(vec1)

# Element-wise operations
elem_add = vec1 .+ vec2
elem_mul = vec1 .* vec2
elem_div = vec1 ./ vec2
elem_pow = vec1 .^ 2

# Matrix creation
mat1 = [1 2 3; 4 5 6; 7 8 9]
mat2 = reshape(1:9, 3, 3)
mat_zeros = zeros(3, 3)
mat_ones = ones(3, 3)
mat_eye = [1 0 0; 0 1 0; 0 0 1]

# Matrix operations
mat_sum = sum(mat1)
mat_transpose = transpose(mat1)
mat_size = size(mat1)
