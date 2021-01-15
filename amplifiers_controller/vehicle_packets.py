from construct import *

START_MAGIC = b'\xda'
PASSIVE_STATE_REQUEST_DATA = bytes.fromhex('02200210000000001800')
ACTIVE_STATUS_REQUEST_DATA = bytes.fromhex('02200510000000001800')


def crc16_xmodem(data):
    msb = 0
    lsb = 0
    for c in data:
        x = c ^ msb
        x ^= (x >> 4)
        msb = (lsb ^ (x >> 3) ^ (x << 4)) & 255
        lsb = (x ^ (x << 5)) & 255
    return Int16ub.build((msb << 8) + lsb)


def calc_vswr(output, reflected):
    return_loss = output - reflected
    return (1 + (10 ** (-return_loss / 20))) / (1 - (10 ** (-return_loss / 20)))


passive_state_response_data_struct = Struct(
    Const(2, Int16ul),
    'output' / Int16ul,
    'reflected' / Int16ul,
    'temperature' / Int16ul,
    'input' / Int16sl,
    'vswr' / IfThenElse(
        this.reflected != this.output,
        Computed(calc_vswr(this.output, this.reflected)),
        Computed(lambda ctx: -1)),
    'rest' / GreedyBytes
)

active_status_response_data_struct = Struct(
    Const(2, Int16ul),
    'is_on' / Flag,
    'unknown_1' / Padding(5),
    'requested_output' / Int16ul,
    'unknown_2' / GreedyBytes
)

active_status_request_data_struct = Struct(
    Const(0x2003, Int16ul),
    Const(b'\x05\x10\x00\x00\x00\x00'),
    'is_on' / Flag,
    Const(b'\x00\x01\x00\x3b\x00'),
    'requested_output' / Int16ul,
    Const(b'\xff\x00\x00\x00\x00\x00\x00\x00\x00\xff\x00\x00\x00')
)

command_struct = Struct(
    'is_request' / Mapping(Bytes(2), {True: b'\x00\x77', False: b'\x77\x00'}),
    'id' / Int32ub,
    'data' / Prefixed(Int16ul, GreedyBytes),
)


def command_to_packet(command):
    return START_MAGIC + command + crc16_xmodem(command)


def command_from_packet(packet):
    return packet[1:-2]
