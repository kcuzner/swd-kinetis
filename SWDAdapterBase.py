import logging

from SWDProtocol import *
from SWDErrors import *

# Refs:
# "Serial Wire Debug and the CoreSightTM Debug and Trace Architecture"


class SWDAdapterBase(object):
    "Base abstract class for SWD adapter hardware"

    def __init__(self):
        self.log = logging.getLogger("comm")

    #
    # Mandatory interface - these must be implemented by hardware
    #

    def writeBits(self, val, num):
        "Write 1-8 bits to SWD"

    def readBits(self, num):
        "Read 1-8 bits from SWD"
        pass

    #
    # Extended interface - these can be expressed in terms of the
    # mandatory interface above (such default implementation is provided),
    # but supporting some of the operations in hardware will make it
    # "hardware accelerated".
    #

    def writeByte(self, val):
        self.writeBits(val, 8)
        self.log.debug("Wrote byte %#x", val)

    def readByte(self):
        return self.readBits(8)

    def writeWord(self, val):
        self.writeByte(val & 0xff)
        val >>= 8
        self.writeByte(val & 0xff)
        val >>= 8
        self.writeByte(val & 0xff)
        val >>= 8
        self.writeByte(val & 0xff)

    def readWord(self):
        val = self.readByte()
        val |= self.readByte() << 8
        val |= self.readByte() << 16
        val |= self.readByte() << 24
        return val

    def turnClk(self):
        "Turn a clock cycle - required when changing comm direction."
        self.readBits(1)

    def readAck(self):
        # ACK transmitted LSB first, so we kinda see it reversed
        return self.readBits(3)

    def writeWordParity(self, val):
        par = self.calcParity(val)
        self.writeWord(val)
        self.writeBits(par, 1)
        self.log.debug("Written word %#x with parity %d", val, par)

    def readWordParity(self):
        val = self.readWord()
        par = self.readBits(1)
        if par != self.calcParity(val):
            raise SWDParityError()
        self.log.debug("Read word %#x with parity %d", val, par)
        return val

    def writeSWD(self, opcode, val):
        self.writeByte(opcode)
        self.turnClk()
        ack = self.readAck()
        self.turnClk()
        if ack != ACK_OK:
            self.handleAck(ack)
        self.writeWordParity(val)

    def readSWD(self, opcode):
        self.writeByte(opcode)
        self.turnClk()
        ack = self.readAck()
        if ack != ACK_OK:
            self.turnClk()
            self.handleAck(ack)
        val = self.readWordParity()
        self.turnClk()
        return val

    def handleAck(self, ack):
        if ack == ACK_WAIT:
            raise SWDWaitError(ack)
        elif ack == ACK_FAULT:
            raise SWDFaultError(ack)
        elif ack == ACK_NOTPRESENT:
            raise SWDNotPresentError(ack)
        else:
            raise SWDProtocolError(ack)

    def resetSWD(self):
        # "It consists of a sequence of 50 clock cycles with data = 1"
        # We send 64 bits
        self.writeWord(0xffffffff)
        self.writeWord(0xffffffff)
        # Unclear why exactly this needed
        self.writeByte(0)
        # "After the host has transmitted a line request sequence to the
        # SW-DP, it must read the IDCODE register."

    def makeOpcode(self, rw, APnDP, addr):
        opcode = 0x81  # Framing
        opcode |= rw | APnDP | addr
        if self.calcParity(opcode):
            opcode |= OP_PARITY
        return opcode

    def readCmd(self, APnDP, addr):
        return self.readSWD(self.makeOpcode(OP_READ, APnDP, addr))

    def writeCmd(self, APnDP, addr, val):
        self.writeSWD(self.makeOpcode(OP_WRITE, APnDP, addr), val)

    def JTAG2SWD(self):
        "Initialize SWD-over-JTAG."
        # Reset JTAG
        self.writeWord(0xffffffff)
#        self.writeWord(0xffffffff)
        # Activate SWD interface
        self.writeByte(0x9e)
        self.writeByte(0xE7)
        return self.resetSWD()

    @staticmethod
    def calcParity(val):
        count = 0
        while val:
            val &= val - 1
            count += 1
        return count & 1
