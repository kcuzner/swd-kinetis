# Kinetis SWD Programmer
### Kevin Cuzner

Partial fork of https://github.com/willdonnelly/pirate-swd and
https://github.com/disk91/PySWD

## Purpose

Provides a simple interface for programming several Kinetis devices which do not
support the more functional EzPort for programming.

## Theory of operation

Each device family that needs to be programmed will have a program written that
resides in RAM which operates the various flash writing peripherals. Several
common locations in memory are read or written by the debug interface to
communicate or check the status of the program while it is executing.

## Particulars

- The TAR will wrap to 1KB. Writing the bytes by groups of 16 (4 word writes)
  seems to avoid problems associated with wrapping too soon.
- Without trapping on resets, the processor reports that it resets because of
  a LOCKUP condition. I suspect the WDT going off, the vector table being set
  up wrong, and then a fault occuring
- Without trapping on resets, it cannot get past setting the WDT register. I
  think that it needs a reset immediately before calling my code. The 128 cycles
  expires before SWD can halt the processor
- For some reason, r15 always quickly goes to fffffffe, even when I have a "b ."
  instruction. I suspect the WDT.
- With trapping on resets, the processor never leaves halt mode :(
    - Clearing the flags didn't seem to help much
