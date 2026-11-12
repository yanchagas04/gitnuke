from loguru import logger
from werkzeug.serving import make_server

from .web import create_app


def main() -> None:
    server = make_server("127.0.0.1", 0, create_app(), threaded=True)
    address = f"http://127.0.0.1:{server.server_port}"
    logger.info("Interface disponivel em {}", address)

    import webbrowser

    if not webbrowser.open(address):
        print(f"Abra este endereco no navegador: {address}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Servidor encerrado.")
    finally:
        server.server_close()


__all__ = ["main"]
