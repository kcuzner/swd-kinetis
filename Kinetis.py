from SWDCommon import *
from SWDErrors import *

class MDM_AP(object):
    """
    MDM-AP port implementation
    """
    def __init__(self, dp, apsel):
        self.dp = dp;
        self.apsel = apsel;

    def idcode(self):
        self.dp.readAP(self.apsel, 0xFC)
        return self.dp.readRB()

    def status(self):
        self.dp.readAP(self.apsel, 0x00)
        return self.dp.readRB()

    def control(self, flash_erase=False, debug_disable=False, debug_request=False,
        reset_request=False, core_hold=False):
        val = 1 << 0 if flash_erase else 0 |\
            1 << 1 if debug_disable else 0 |\
            1 << 2 if debug_request else 0 |\
            1 << 3 if reset_request else 0 |\
            1 << 4 if core_hold else 0
        self.dp.writeAP(self.apsel, 0x04, val)
        return self.dp.readRB()

    def get_control(self):
        self.db.readAP(self.apsel)
        return self.dp.readRB()

class Kinetis(object):
    DFSR  = 0xE000ED30 # Debug fault status register
    DHCSR = 0xE000EDF0 # halting status and control register
    DCRSR = 0xE000EDF4 # debug core register selector
    DCRDR = 0xE000EDF8 # debug core data register
    DEMCR = 0xE000EDFC # debug exception monitor and control register

    AIRCR = 0xE000ED0C # Application interrupt and reset control register
    VTOR  = 0xE000ED08 # Vector table offset register


    def __init__(self, debugPort):
        self.ahb = MEM_AP(debugPort, 0) # MEM-AP is located at access port 0
        #self.mdm = MDM_AP(debugPort, 1) # MDM-AP is located at access port 1

    def __str__(self):
        """
        Describes the current device with its debug status
        """
        lst = []
        lst.append("AHB-AP: 0x{0:x}".format(self.ahb.idcode()))
        #lst.append("MDM-AP: 0x{0:x}".format(self.mdm.idcode()))
        return '\n'.join(lst)

    def registers(self, reg=None, value=None, output_hex=True):
        """
        Gets or sets the registers
        """
        registers = range(0, 16) if reg is None else [reg]
        if value is None:
            return [(t[0], hex(t[1]) if output_hex else t[1]) for t in\
                [(i, self.get_r(i)) for i in registers]]
        else:
            for i in registers:
                self.set_r(i, value)

    def status(self, output_hex=True):
        """
        Returns a list of tuples describing the device status
        """
        lst = []
        lst.append(("AHB-AP", self.ahb.status()))
        #lst.append(("MDM-AP", self.mdm.status()))
        lst.append(("DHCSR", self.ahb.readWord(Kinetis.DHCSR)))
        lst.append(("DFSR", self.ahb.readWord(Kinetis.DFSR)))
        return [(l[0], hex(l[1])) if output_hex else l for l in lst]

    def set_debug(self):
        """
        Activates debug mode without halting the processor
        """
        self.ahb.writeWord(Kinetis.DHCSR, 0xA05F0001)

    def halt(self, reset=False):
        """
        Places the device in halt

        ARMv6
        """
        self.ahb.writeWord(Kinetis.DHCSR, 0xA05F0003)

    def reset(self):
        """
        Resets the device, activating halt once the reset completes

        MDM-AP
        """
        self.ahb.writeWord(Kinetis.DEMCR, 0x1) #enable core catch
        self.ahb.readWord(Kinetis.DHCSR) # clear reset flag
        self.ahb.writeWord(Kinetis.AIRCR, 0x05FA0004) # request reset
        while not (self.ahb.readWord(Kinetis.DHCSR & 0x02000000)): # wait
            time.sleep(0.1)

    def run(self):
        """
        Returns the device to normal operation

        ARMv6 and MDM-AP
        """
        self.ahb.writeWord(Kinetis.DEMCR, 0x0)
        self.ahb.writeWord(Kinetis.DHCSR, 0xA05F0000)
        r = self.ahb.readWord(Kinetis.DFSR)
        self.ahb.writeWord(Kinetis.DFSR, r)
        #self.mdm.control()

    # Kinetis stuff

    def get_r(self, r):
        self.ahb.writeWord(Kinetis.DCRSR, r & 0x1F)
        while not (self.ahb.readWord(Kinetis.DHCSR) & 0x10000):
            time.sleep(0.1)
        return self.ahb.readWord(Kinetis.DCRDR)

    def set_r(self, r, val):
        self.ahb.writeWord(Kinetis.DCRDR, val)
        self.ahb.writeWord(Kinetis.DCRSR, 0x10000 | (r & 0x1F))
        while not (self.ahb.readWord(Kinetis.DHCSR) & 0x10000):
            time.sleep(0.1)

    def vtor(self, addr=None):
        if addr is not None:
            self.ahb.writeWord(Kinetis.VTOR, addr)
        else:
            v = self.ahb.readWord(Kinetis.VTOR)
            return v

    # writes data to an address
    def write_to_ram(self, addr, data):
        """
        Writes a stream of 8-bit values to RAM
        """
        if any([d > 0xFF for d in data]):
            raise InvalidDataException("Data contains values greater than 0xFF")
        # pad array with zeros to be divisible by 4
        if len(data) % 4:
            data[len(data):] = [0] * (4 - (len(data) % 4))
            print("Now", len(data))

        # convert to 32-bit values for speed
        a_data = [(data[i+3] << 24) + (data[i+2] << 16) + (data[i+1] << 8) + \
            data[i] for i in range(0, len(data), 4)]
        self.ahb.writeBlock(addr, a_data)
