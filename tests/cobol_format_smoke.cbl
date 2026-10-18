identification division.
program-id. ZMIRROR-FORMAT-SMOKE.
environment division.
input-output section.
file-control.
    select input-file assign to dynamic input-path
        organization is line sequential
        file status is ws-file-status.
data division.
file section.
fd input-file
    record is varying in size from 1 to 256 characters
    depending on ws-record-length.
01 input-record pic x(256).
working-storage section.
01 input-path pic x(512).
01 ws-file-status pic xx.
01 ws-record-length pic 9(4) comp.
01 ws-record-count pic 9(8) value 0.
01 ws-error-count pic 9(8) value 0.
01 ws-eof pic x value 'N'.
01 ws-age pic x(3).
01 ws-sign pic x.
01 ws-balance pic x(7).
01 ws-outcome pic x.
procedure division.
    accept input-path from command-line
    if input-path = spaces
        display 'ERROR: provide input file path as argument.'
        move 2 to return-code
        stop run
    end-if

    open input input-file
    if ws-file-status not = '00'
        display 'ERROR: cannot open input; file status=' ws-file-status
        move 2 to return-code
        stop run
    end-if

    perform until ws-eof = 'Y'
        read input-file
            at end
                move 'Y' to ws-eof
            not at end
                add 1 to ws-record-count
                move input-record(1:3) to ws-age
                move input-record(4:1) to ws-sign
                move input-record(5:7) to ws-balance
                move input-record(12:1) to ws-outcome
                if ws-record-length = 12
                    and ws-age is numeric
                    and (ws-sign = '+' or ws-sign = '-')
                    and ws-balance is numeric
                    and (ws-outcome = 'Y' or ws-outcome = 'N')
                    continue
                else
                    add 1 to ws-error-count
                    display 'INVALID RECORD #' ws-record-count
                end-if
        end-read
    end-perform

    close input-file
    display 'Records read: ' ws-record-count
    display 'Invalid records: ' ws-error-count
    if ws-record-count > 0 and ws-error-count = 0
        display 'COBOL FORMAT SMOKE TEST: PASS'
        move 0 to return-code
    else
        display 'COBOL FORMAT SMOKE TEST: FAIL'
        move 1 to return-code
    end-if
    stop run.
