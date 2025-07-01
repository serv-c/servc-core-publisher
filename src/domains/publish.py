import json
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError
from pyspark.sql import SparkSession
from servc.svc.com.worker.types import RESOLVER_CONTEXT
from servc.svc.io.output import InvalidInputsException
from servc.util import findType
from servc_typings.com.db import Database
from servc_typings.domains.data import engineOptions
from servc_typings.domains.publisher import PublishOptions, PublishType
from servc_typings.tables.publish_record import PUBLISH_RECORDS

from src.publishers import publishingEngines


def publish(id: str, raw_payload: Any, context: RESOLVER_CONTEXT) -> bool:
    try:
        payload = PublishOptions.model_validate(raw_payload)
    except ValidationError as e:
        raise InvalidInputsException(str(e))
    db = findType(context["middlewares"], Database)
    publish_records = findType(context["middlewares"], PUBLISH_RECORDS)

    # validate the publish type is valid
    if payload.type not in [PublishType.WAREHOUSE.value, PublishType.DELTA.value]:
        raise InvalidInputsException(f"Invalid publish type: {payload.type}")
    publish_type = PublishType(payload.type)
    if publish_type not in publishingEngines:
        raise InvalidInputsException(
            f"Publishing engine not found for type: {payload.type}"
        )

    # generate the dataset_id
    dataset_id: str = re.sub(
        r"[^a-z0-9_]+",
        "",
        "_".join([payload.tenant_name, payload.app_id, str(uuid.uuid4())[:10]]).lower(),
    )

    # check if the dataset exists already
    existing_datasets = db.query(
        "SELECT dataset_id FROM datasets WHERE app_id = :app_id AND auth_expression = :tenant_name",
        {"app_id": payload.app_id, "tenant_name": payload.tenant_name},
    )
    if len(existing_datasets) > 0:
        dataset_id = str(existing_datasets[0]["dataset_id"])

    # create the spark context
    pod_id = os.environ.get("POD_IP", "127.0.0.1")
    spark = (
        SparkSession.builder.appName("publisher")  # type: ignore
        .config("spark.driver.host", pod_id)
        .config(map=payload.sparkConfig)  # type: ignore
        .getOrCreate()
    )

    # pass job to the correct publishing function
    location_type, options = publishingEngines[publish_type](
        context["config"], dataset_id, payload.options, spark
    )
    spark.stop()

    # validate we should publish this dataset
    if location_type not in engineOptions:
        raise InvalidInputsException(
            f"Invalid location type: {location_type}. Must be one of {list(engineOptions.keys())}"
        )

    # insert the dataset into the database
    if len(existing_datasets) > 0:
        db.query(
            """
            UPDATE datasets
            SET location_type = :location_type, details = :details
            WHERE app_id = :app_id AND auth_expression = :tenant_name
            """,
            {
                "app_id": payload.app_id,
                "tenant_name": payload.tenant_name,
                "location_type": location_type,
                "details": json.dumps(options),
            },
            return_rows=False,
            commit=True,
        )
    else:
        db.query(
            """
            INSERT INTO datasets (
                dataset_id, app_id, auth_expression, location_type, details
            ) VALUES (
                :dataset_id, :app_id, :tenant_name, :location_type, :details
            )
            """,
            {
                "dataset_id": dataset_id,
                "app_id": payload.app_id,
                "tenant_name": payload.tenant_name,
                "location_type": location_type,
                "details": json.dumps(options),
            },
            return_rows=False,
            commit=True,
        )

    # add to the system of record for publishing
    publish_records.insert(
        [
            {
                "app_id": payload.app_id,
                "tenant_name": payload.tenant_name,
                "dataset_id": dataset_id,
                "job_id": payload.job_id,
                "publish_type": payload.type,
                "payload": json.dumps(raw_payload),
                "time": datetime.now(timezone.utc),
            }
        ]
    )

    return True
