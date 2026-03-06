program factorial_program
    implicit none
    integer :: n, result

    read *, n

    if (n < 0) then
        print *, "Error: Negative input"
        stop 1
    end if

    result = factorial(n)
    print *, result

contains

    recursive function factorial(x) result(fact)
        integer, intent(in) :: x
        integer :: fact

        if (x <= 1) then
            fact = 1
        else
            fact = x * factorial(x - 1)
        end if
    end function factorial

end program factorial_program
