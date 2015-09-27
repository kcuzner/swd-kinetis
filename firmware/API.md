# API Definition

For each device supported, an appropriately named folder must be present (named
the same as the identifier used in the arguments to swd-kinetis). The firmware
must be located in a file called `./bin/firmware.hex`. A file called
`./bin/firmware.map` must also be present which is the gcc linker-generated map
file.

## Theory of operation

The firmware provides a common abstract interface for erasing and writing the
flash. It must perform the following operations:

 * Mass erase. If the device is locked, the SWD programmer will need to perform
   the mass erase operation via the MDM-AP (the need for this can be checked via
   the MDM-AP as well). Otherwise, the program can perform this command.
 * Program and verify block. This will not allow programming of the flash
   configuration region from 0x0400 to 0x040F (this region size seems to be
   relatively common between Kinetis devices that I've read the manuals for)
 * Program 16-byte flash configuration region.

## Linker and section names

The following code sections are required and should appear in the gcc map
file:

 * .interrupt_vector_table
 * .unsecured_config
 * .flash_api_state

All of these should be found in the hex file as well as data must be read from
them and we don't yet support elf formats.

.interrupt_vector_table must have the address of the interrupt vector table as
required by VTOR. The data at this location will be read to determine the
initial stack pointer and program counter.

.unsecured_config must contain 16 bytes which will be written to the flash
configuration section in the event of an error to ensure the device remains
unsecure.

.flash_api_state must have the address to a block of memory conforming to the
following structure and declaration:

```
    typedef struct
    {
        volatile uint32_t status;
        volatile uint32_t address;
        volatile uint32_t length;
        volatile uint32_t buffer[64];
        } APIState;

    __attribute__((section (".flash_api_state"), used))
    APIState FlashAPIState;
```

## APIState Format

### status

Communicates programmer status and initiates commands

 * Bit 0-2: Program command:
   * 0b000 - Mass erase
   * 0b001 - Program block
   * 0b010 - Program configuration
 * Bit 3: Ready/start: Firmware will set to 1 when the program is ready to
   accept commands, provided the status code is consistent. The debugger should
   write to 0 in order to initiate a program command.
 * Bit 4-7: Status code valid when bit 3 is set to 1
   * 0b0000 - OK, command complete
   * 0b0002 - A flash error occurred
   * 0b1111 - Command not implemented
 * Bit 8-15: Error flags (can vary by implementation)
 * All other bits to bit 31: Reserved, write to 0

### address

Address to write location of next chunk. Must be aligned to a 4-byte boundary.

### buffer

Memory from this location until buffer+buffer_max_length can be written as a
data buffer for the flash. The buffer is expressed as a 4-byte words.

### length

32-bit value containing the length of the current flash buffer in 4-byte words
