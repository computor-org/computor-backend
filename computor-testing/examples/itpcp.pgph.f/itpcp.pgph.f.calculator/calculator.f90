program calculator
    implicit none
    real :: a, b, result
    character(len=100) :: line
    character(len=10) :: op_str
    integer :: pos1, pos2

    ! Read entire line (e.g., "5 + 3" or "20 / 4")
    read '(A)', line

    ! Parse: find first and second spaces
    line = adjustl(line)
    pos1 = index(line, ' ')
    read(line(1:pos1-1), *) a

    line = adjustl(line(pos1+1:))
    pos2 = index(line, ' ')
    op_str = trim(line(1:pos2-1))

    read(line(pos2+1:), *) b

    select case (trim(op_str))
        case ('+')
            result = a + b
        case ('-')
            result = a - b
        case ('*')
            result = a * b
        case ('/')
            if (abs(b) < 1.0e-10) then
                print *, "Error: Division by zero"
                stop 1
            end if
            result = a / b
        case default
            print *, "Error: Unknown operator"
            stop 1
    end select

    print *, result

end program calculator
