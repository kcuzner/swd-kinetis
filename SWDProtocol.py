# Refs:
# "Serial Wire Debug and the CoreSightTM Debug and Trace Architecture"

# Note: ACK is transmitted LSB first, so patterns
# below are reversed comparing to ARMDIv5 diagrams, but matches
# values used in text (sec. 5.4.2 and on)
ACK_OK = 0b001
ACK_WAIT = 0b010
ACK_FAULT = 0b100
# Additional code not defined in ARMDIv5 - when target not present/
# doesn't respond, line is pulled high and that's what we read
ACK_NOTPRESENT = 0b111

# Same note on bit order applies
OP_AP = 0x02
OP_DP = 0x00
OP_READ = 0x04
OP_WRITE = 0x00
OP_PARITY = 0x20
