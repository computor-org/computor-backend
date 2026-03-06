/* Simple Calculator - Wrong Student Solution */
#include <stdio.h>

int main() {
    int a, b;

    printf("Enter first number: ");
    scanf("%d", &a);

    printf("Enter second number: ");
    scanf("%d", &b);

    /* WRONG: switched sum and difference */
    printf("Sum: %d\n", a - b);
    printf("Difference: %d\n", a + b);
    printf("Product: %d\n", a * b);

    /* Missing division by zero check */
    printf("Quotient: %d\n", a / b);

    return 0;
}
