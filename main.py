#!/usr/bin/env python

from servc.server import start_server
from servc_typings.com.db import Database

from src.config import QUEUE_NAME
from src.domains.publish import publish
from src.pytype import PUBLISH_RECORDS


def main():
    return start_server(
        resolver={
            "publish": publish,
        },
        route=QUEUE_NAME,
        components=[Database, PUBLISH_RECORDS],
    )


if __name__ == "__main__":
    main()
