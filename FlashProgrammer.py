"""
Handles flash programming Kinetis devices
"""

import re

class IntelHexException(Exception):
    def __init__(self, message):
        super(Exception, self).__init__(message)

class InvalidDataException(Exception):
    def __init__(self, message):
        super(Exception, self).__init__(message)

class HexLine(object):
    def __init__(self, s):
        vals = [int(s[i:i+2], 16) for i in range(0, len(s), 2)]
        if len(vals) < 5:
            raise IntelHexException("Invalid line length")
        if vals[0] != (len(vals) - 5):
            raise IntelHexException("Invalid data length")
        self.count = vals[0]
        self.addr = (vals[1] << 8) + vals[2]
        self.type = vals[3]
        self.data = vals[4:len(vals)-1]
        cs = (~(sum(vals[0:len(vals)-1]) & 0xFF) + 1) & 0xFF
        if cs != vals[len(vals)-1]:
            raise IntelHexException("Invalid checksum")

    def __str__(self):
        return "<HexLine count={0} addr={1:x} type={2:x}>".format(self.count,\
            self.addr, self.type)

def read_intel_hex_raw(name):
    """
    Returns a sequence of HexLine objects representing an intel hex file
    """
    LINE_FORMAT = re.compile('^:((?:[\dA-Fa-f]{2})+)$')
    with open(name) as f:
        for line in f:
            if line is None:
                return
            match = LINE_FORMAT.match(line)
            if match is None:
                raise IntelHexException("Bad line format")
            group = match.group(1)
            yield HexLine(group)

def parse_intel_hex(name):
    """
    Parses an intel hex file, returning tuples of addresses and data bytes
    """
    esaddr = 0 # extended segment address
    eladdr = 0 # extended linear address
    for l in read_intel_hex_raw(name):
        if l.type == 0x00: # data
            yield ((eladdr << 16) + esaddr * 16 + l.addr, l.data)
        elif l.type == 0x01: # end of file
            return
        elif l.type == 0x02: # extended segment address
            if len(l.data) != 2:
                raise IntelHexException("Invalid data length for extended \
                    segment address")
            esaddr = (l.data[0] << 8) + l.data[1]
        elif l.type == 0x04: # extended linear address
            if len(l.data) != 2:
                raise IntelHexException("Invalid data length for extended \
                    linear address")
            eladdr = (l.data[0] << 8) + l.data[1]
        elif l.type == 0x05: # Start linear address
            # This represents the 32-bit value loaded into the EIP register.
            # In the context of ARM, this is the entry point...which we ignore
            # for now
            pass
        else:
            raise IntelHexException("Unimplmented type {0}".format(l.type))

def read_map_raw(name):
    """
    Reads a GCC map file to get addresses of sections
    Returns a sequence of tuples
    """
    MAP_LINE_FORMAT = re.compile('^ \.([\w]+)\s+0x([\da-f]+)', re.M)
    with open(name) as f:
        lines = '\n'.join(f)
        for match in MAP_LINE_FORMAT.finditer(lines):
            yield (match.group(1), int(match.group(2), 16))

def read_map(name):
    """
    Reads a GCC map file to get addresses of sections
    Returns a dictionary
    """
    return dict(read_map_raw(name))

class FlashProgrammer(object):
    def __init__(self, dev, type):
        """
        Initializes the flash programmer
        dev: The device to program
        type: The string type name of the device
        """
        self.dev = dev
        self.type = type

    def program(self, filename):
        """
        Programs the passed hex file to the device
        """
        mapfile = read_map('firmware/' + self.type + '/bin/firmware.map')
        table_offset = mapfile['interrupt_vector_table']
        flash_api_loc = mapfile['flash_api_state']

        print("Device: {0}\n\tIVT: {1:x}\n\tAPI: {2:x}".format(
            self.type, table_offset, flash_api_loc))

        print(self.dev.status())
        self.dev.set_debug()
        print("SIM_SRSID", hex(self.dev.ahb.readWord(0x40048000)))
        self.dev.reset() # this eventually halts the processor
        print(self.dev.status())
        print(self.dev)
        print(self.dev.registers())
        for (addr, data) in parse_intel_hex('firmware/' + self.type + '/bin/firmware.hex'):
            print("Writing {0} bytes to {1:x}".format(len(data), addr))
            self.dev.write_to_ram(addr, data)
        print(self.dev.status())
        stack_top = self.dev.ahb.readWord(table_offset)
        reset_vec = self.dev.ahb.readWord(table_offset + 4)
        print("\tSP: 0x{0:x}".format(stack_top))
        print("\tReset vector: 0x{0:x}".format(reset_vec))
        self.dev.registers(reg=0xd, value=stack_top)
        self.dev.registers(reg=0xf, value=reset_vec)
        self.dev.run()
        print(self.dev.status())
