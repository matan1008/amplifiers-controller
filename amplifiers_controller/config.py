from pydantic import BaseSettings


class Settings(BaseSettings):
    amplifiers_ip_addresses: list[str] = ['192.168.1.100', '192.168.1.101', '192.168.1.102']
    amplifiers_names: list[str] = ['900 A', '900 B', '1800']
    amplifier_connection_timeout: float = 0.2  # In seconds
    run: bool = True
