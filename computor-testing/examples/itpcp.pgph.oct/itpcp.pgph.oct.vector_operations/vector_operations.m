% Vector operations in Octave
% Student template

% Create vectors
v1 = [1, 2, 3, 4, 5];
v2 = linspace(0, 10, 5);

% Vector operations
v_sum = v1 + v2;
v_prod = v1 .* v2;
dot_product = dot(v1, v2);
v_length = length(v1);

% Matrix creation
M = [1, 2, 3; 4, 5, 6; 7, 8, 9];
M_transpose = M';
M_det = det(M);
