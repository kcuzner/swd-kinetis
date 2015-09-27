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
        elif l.type == 0x03: # Start segment address
            # This represents the CS:IP value for 8086 and has no meaning for
            # us here right now
            pass
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

def aggregate_addr_data(addrdata, max_length=256):
    """
    Aggregates contiguous data into blocks with a maximum length
    """
    current_addr = None
    next_addr = None
    current_data = []
    for (addr, data) in addrdata:
        if next_addr != addr or len(current_data) >= max_length:
            if current_addr is not None:
                yield (current_addr, current_data)
            current_addr = addr
            current_data = data
            next_addr = current_addr + len(data)
        else:
            current_data.extend(data)
            next_addr += len(data)
    if current_addr is not None:
        yield (current_addr, current_data)


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

def extract_bytes(words):
    for w in words:
        yield w & 0xFF
        yield (w >> 8) & 0xFF
        yield (w >> 16) & 0xFF
        yield (w >> 24) & 0xFF

class FlashProgrammer(object):
    def __init__(self, dev, type):
        """
        Initializes the flash programmer
        dev: The device to program
        type: The string type name of the device
        """
        self.dev = dev
        self.type = type
        mapfile = read_map('firmware/' + self.type + '/bin/firmware.map')
        self.__table_offset = mapfile['interrupt_vector_table']
        self.__flash_api_loc = mapfile['flash_api_state']
        self.__unsecured_config_loc = mapfile['unsecured_config']

    def program(self, filename):
        """
        Programs the passed hex file to the device
        """


        print("Device: {0}\n\tIVT: {1:x}\n\tAPI: {2:x}".format(
            self.type, self.__table_offset, self.__flash_api_loc))

        if self.dev.is_secured():
            print("Device reports that it is secure. Attempting to unsecure...")
            if self.dev.unsecure():
                print("Device is still secure. Aborting.")
                return

        print(self.dev)
        print("{0:x}".format(self.dev.mdm.status()))
        print(self.dev.status())
        self.dev.set_debug()
        print("SIM_SRSID", hex(self.dev.ahb.readWord(0x40048000)))
        self.dev.reset() # this eventually halts the processor
        print(self.dev.status())
        print(self.dev)
        print("Loading {0} firmware into memory...".format(self.type))
        for (addr, data) in aggregate_addr_data(parse_intel_hex('firmware/' + self.type + '/bin/firmware.hex')):
            print("\tWriting {0} bytes to {1:x}".format(len(data), addr))
            self.dev.write_to_ram(addr, data)
        print("Firmware loaded.")
        print(self.dev.status())
        stack_top = self.dev.ahb.readWord(self.__table_offset)
        reset_vec = self.dev.ahb.readWord(self.__table_offset + 4)
        print("\tSP: 0x{0:x}".format(stack_top))
        print("\tReset vector: 0x{0:x}".format(reset_vec))
        self.dev.registers(reg=0xd, value=stack_top)
        self.dev.registers(reg=0xf, value=reset_vec)
        self.dev.run()
        self.dev.wait_flash()
        print(self.dev.status())

        try:
            self.__mass_erase()
            print("Programming {0}...".format(filename))
            for (addr, data) in aggregate_addr_data(parse_intel_hex(filename)):
                print("\tWriting {0} bytes to {1:x}".format(len(data), addr))
                self.__program_flash(addr, data)
        except:
            print("An error occurred. Erasing and unsecuring flash...")
            self.__mass_erase()
            self.__program_flash(0x400, list(extract_bytes(self.dev.ahb.readBlock(self.__unsecured_config_loc, 4))))
            print("Done.")
            raise

        print("After programming, the flash configuration is:")
        for i in [0x400, 0x404, 0x408, 0x40C]:
            print("{0:x}: {1:x}".format(i, self.dev.ahb.readWord(i)))

        self.dev.reset()
        self.dev.run()

    def __wait_ready(self):
        """
        Waits for the firmware to become ready
        """
        while not self.dev.ahb.readWord(self.__flash_api_loc) & 0x8:
            i = 0
        return self.dev.ahb.readWord(self.__flash_api_loc)

    def __mass_erase(self):
        """
        Performs a mass erase operation via the firmware
        """
        print("Waiting for firmware to become ready...")
        status = self.__wait_ready()
        if (status & 0xF0):
            print("There is an error pending: {0:x}".format(status))
            return
        print("Issuing erase command")
        self.dev.ahb.writeWord(self.__flash_api_loc, 0x00)
        status = self.__wait_ready()
        if (status & 0xF0):
            print("There is an error pending: {0:x}".format(status))
            return
        print("Mass erase complete")

    def __program_flash(self, addr, data):
        """
        Programs a set of data
        """
        if any([d > 0xFF for d in data]):
            raise InvalidDataException("Data contains values greater than 0xFF")
        # pad array with zeros to be divisible by 4
        if len(data) % 4:
            data[len(data):] = [0] * (4 - (len(data) % 4))

        # convert to 32-bit values for speed
        a_data = [(data[i+3] << 24) + (data[i+2] << 16) + (data[i+1] << 8) + \
            data[i] for i in range(0, len(data), 4)]

        self.dev.ahb.writeWord(self.__flash_api_loc + 4, addr)
        self.dev.ahb.writeWord(self.__flash_api_loc + 8, len(a_data))
        for i in range(0, len(a_data)):
            self.dev.ahb.writeWord(self.__flash_api_loc + 12 + i * 4, a_data[i])
        self.dev.ahb.writeWord(self.__flash_api_loc, 0x01)
        status = self.__wait_ready()
        if (status & 0xF0):
            print("There is an error pending: {0:x}".format(status))
            return
