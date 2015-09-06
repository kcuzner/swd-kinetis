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
