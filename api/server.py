from fire import Fire

import dependency_resolver
from main import launch, start, stop
from utils.logging import logger

from dareplane_utils.default_server.server import DefaultServer
from main import configuration_resolver


def main(port: int = None, ip: str = None, loglevel: int = 10):
    logger.setLevel(loglevel)

    if ip is None:
        ip = configuration_resolver.get('host')
    if port is None:
        port = configuration_resolver.get('port')

    pcommand_map = {
        "LAUNCH": launch, 
        "START PROJECTOR": start,
        "STOP PROJECTOR": stop
    }

    server = DefaultServer(
        port, ip=ip, pcommand_map=pcommand_map, name="ONEP_server"
    )

    # initialize to start the socket
    logger.info(f"initiating ONEP server at {ip}:{port}")
    server.init_server()
    # start processing of the server
    logger.info("listening...")
    server.start_listening()

    return 0


if __name__ == "__main__":
    Fire(main)
