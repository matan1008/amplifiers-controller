import asyncio

import construct

from .vehicle_packets import *


class Amplifier:
    AMPLIFIERS_CONTROL_PORT = 10001
    REPORT_QUERY_INTERVAL = 0.1  # In Seconds

    def __init__(self, index: int, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.index = index
        self._reader = reader
        self._writer = writer
        self._command_id = 0x0199e447

    async def change_output(self, output: int):
        """
        Change the amplifier output.
        :param int output: Request output
        """
        await self._request_amplifier(
            active_status_request_data_struct.build({'is_on': True, 'requested_output': output})
        )

    async def start_getting_reports(self, reports_queue: asyncio.Queue):
        """
        Start querying the amplifier for data about its state - output, input, temperature and more.
        :param asyncio.Queue reports_queue: Queue to put the fetched reports in.
        """
        while True:
            try:
                parsed = await self._request_amplifier(PASSIVE_STATE_REQUEST_DATA)
                passive_data = passive_state_response_data_struct.parse(parsed)
                parsed = await self._request_amplifier(ACTIVE_STATUS_REQUEST_DATA)
                active_data = active_status_response_data_struct.parse(parsed)
            except (ConnectionError, construct.ConstructError):
                # Probably connection released
                return
            await reports_queue.put({
                'index': self.index,
                'report': {
                    'output': passive_data.output,
                    'input': passive_data.input,
                    'reflected': passive_data.reflected,
                    'vswr': passive_data.vswr,
                    'temperature': passive_data.temperature,
                    'requested_output': active_data.requested_output,
                }
            })

            await asyncio.sleep(self.REPORT_QUERY_INTERVAL)

    @staticmethod
    async def create_amplifier(index: int, ip: str, port=AMPLIFIERS_CONTROL_PORT):
        """
        Connect to an amplifier and return a wrapper to that connection.
        :param int index: Amplifier's index, used for reporting data.
        :param str ip: IP Address of the amplifier.
        :param int port: Amplifier's control port.
        :return: Object that represents the amplifier.
        :rtype: Amplifier
        """
        reader, writer = await asyncio.open_connection(ip, port)
        return Amplifier(index, reader, writer)

    def _get_new_command_id(self) -> int:
        """
        Generate a new command id.
        :return: New command id to be used.
        :rtype: int
        """
        self._command_id = (self._command_id + 1) % 0x100000000
        return self._command_id

    async def _request_amplifier(self, data: bytes) -> bytes:
        """
        Send a command to the amplifier and wait for a response.
        :param bytes data: Command's data to send.
        :return: The data of the amplifier's response.
        :rtype: bytes
        """
        command_id = self._get_new_command_id()
        command = command_struct.build({'is_request': True, 'id': command_id, 'data': data})
        self._writer.write(command_to_packet(command))
        await self._writer.drain()
        # Wait for a response with the same command id the we sent.
        while True:
            parsed = command_struct.parse(command_from_packet(await self._reader.read(1024)))
            if parsed.id == command_id and not parsed.is_request:
                return parsed.data
