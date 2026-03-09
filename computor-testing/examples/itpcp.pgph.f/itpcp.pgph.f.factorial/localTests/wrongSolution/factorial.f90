program factorial_program
    implicit none
    integer :: n, result

    read *, n

    ! Bug: Missing negative check

    result = factorial(n)
    print *, result

contains

    recursive function factorial(x) result(fact)
        integer, intent(in) :: x
        integer :: fact

        ! Bug: base case is wrong (should be <= 1, not == 0)
        if (x == 0) then
            fact = 1
        else
            fact = x * factorial(x - 1)
        end if
    end function factorial

end program factorial_program
