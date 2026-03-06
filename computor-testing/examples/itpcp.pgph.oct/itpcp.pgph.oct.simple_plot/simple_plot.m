% Simple plot in Octave
% Student template

% Create data
x = linspace(0, 2*pi, 100);
y_sin = sin(x);
y_cos = cos(x);

% Create figure
figure(1);
plot(x, y_sin, 'b-', x, y_cos, 'r--');
xlabel('x');
ylabel('y');
title('Sine and Cosine');
legend('sin(x)', 'cos(x)');
grid on;
