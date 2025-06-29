import json
import uuid

from servc.svc.config import Config
from servc_typings.com.db import Database

from tests.schema import QUERIES


# TODO: better way to insert tables
def init_db():
    config = Config()
    db = Database(config.get(f"conf.{Database.name}"))
    for query in QUERIES:
        db.query(query, commit=True, return_rows=False)
    db.close()


payload = {
    "app_id": "chess",
    "profile_id": "yusuf",
}


def insert_dataset(
    location_type: str,
    details: dict,
    auth_expression: str = payload["profile_id"],
    app_id: str = payload["app_id"],
    dataset_id: str | None = None,
):
    id = dataset_id if dataset_id else str(uuid.uuid4())
    config = Config()
    db = Database(config.get(f"conf.{Database.name}"))

    db.query(
        """
        INSERT INTO datasets (dataset_id, location_type, details, auth_expression, app_id)
        VALUES (:dataset_id, :location_type, :details, :auth_expression, :app_id)
        """,
        {
            "dataset_id": id,
            "location_type": location_type,
            "details": json.dumps(details),
            "auth_expression": auth_expression,
            "app_id": app_id,
        },
        commit=True,
        return_rows=False,
    )
    db.close()
    return id
