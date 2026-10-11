* smoke.s - assembles only with maclib370's macros (tools/smoke.sh):
* SAVE/RETURN/WTO/GETMAIN from SYS1.MACLIB, GETMAIN with LOC= (TK5's
* ZP60033), SPIE and TIME (absent from libc370's copies), and the CVT
* DSECT from SYS1.AMODGEN.
SMOKE    CSECT
         SAVE  (14,12),,SMOKE
         LR    12,15
         USING SMOKE,12
         SPIE  MF=L
         TIME  DEC
         GETMAIN RC,LV=64,SP=0,LOC=BELOW
         WTO   'SMOKE'
         L     2,16
         USING CVT,2
         RETURN (14,12),RC=0
         CVT   DSECT=YES
         END   SMOKE
