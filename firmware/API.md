# API Definition

For each device supported, an appropriately named folder must be present (named
the same as the identifier used in the arguments to swd-kinetis). The firmware
must be located in a file called `bin/firmware.hex`. A file called
`./map.json` must also be present which specifies the memory addresses used to
communicate to the firmware.

# JSON Format

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

# Memory format

## status

Bit | 31-1 | 0
--- | --- | ---
Name | Reserved | Ready/Start
--- | --- | ---
Description | Reserved bits (write to 0) | When 1, the program signals that it is ready to write. This will be set to 0 to initiate a write
