# API Definition

For each device supported, an appropriately named folder must be present (named
the same as the identifier used in the arguments to swd-kinetis). The firmware
must be located in a file called `bin/firmware.hex`. A file called
`./map.json` must also be present which specifies the memory addresses used to
communicate to the firmware.

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

## JSON Map Format

```
{
  "table_offset": "0x<hex location of the ISR table in the program>"
  "status_reg": "0x<hex location of the 32-bit status word>",
  "address_reg": "0x<hex location to write start address of next chunk>"
  "length_reg": "0x<hex location to write length of next chunk>"
  "buffer_reg": "0x<hex location of the start of the program buffer>",
  "buffer_max_length": "<decimal length of the program buffer>"
}
```

## Memory format

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
   * 0b0001 - Flash is secure, unable to execute any command
   * 0b1111 - Command not implemented
 * All other bits to bit 31: Reserved, write to 0

### address

Address to write location of next chunk. Must be aligned to a 4-byte boundary.

### buffer

Memory from this location until buffer+buffer_max_length can be written as a
data buffer for the flash

### length

32-bit value containing the length of the current flash buffer.
