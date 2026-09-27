set n=115
:loop

diff PL%n%.yaml ..\..\ECC4TrkLst2\PL%n%.yaml 
set /a n=n+1

if %n% gtr 133 goto :eof
goto :loop
