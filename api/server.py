from fire import Fire

import dependency_resolver
from main import launch, start, stop
from utils.logging import logger

from dareplane_utils.default_server.server import DefaultServer
from main import configuration_resolver

def main(port: int = 8086, ip: str = "127.0.0.1", loglevel: int = 10):
    logger.setLevel(loglevel)

    ip = configuration_resolver.get('host')
    port = configuration_resolver.get('port')

    pcommand_map = {
        "LAUNCH": launch, 
        "START PROJECTOR": start,
        "STOP PROJECTOR": stop
    }

    server = DefaultServer(
        port, ip=ip, pcommand_map=pcommand_map, name="projecotr_control_server"
    )

    # initialize to start the socket
    server.init_server()
    # start processing of the server
    server.start_listening()

    return 0


if __name__ == "__main__":
    Fire(main)
