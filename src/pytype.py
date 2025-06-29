from datetime import datetime
from typing import TypedDict

import pyiceberg.types as types
from pydantic import TypeAdapter
from pyiceberg.schema import Schema
from servc.svc.com.storage.iceberg import IceBerg
from servc.svc.com.storage.lake import LakeTable, Medallion


class PublishRecord(TypedDict):
    app_id: str
    tenant_name: str
    dataset_id: str
    job_id: str
    publish_type: str
    payload: str
    time: datetime


PublishRecordModel = TypeAdapter(PublishRecord)

PUBLISH_RECORDS_SCHEMA: LakeTable = {
    "name": "publishing_records",
    "medallion": Medallion.GOLD,
    "partitions": ["app_id", "tenant_name"],
    "schema": Schema(
        types.NestedField(
            field_id=1, name="app_id", type=types.StringType(), required=True
        ),
        types.NestedField(
            field_id=2, name="tenant_name", type=types.StringType(), required=True
        ),
        types.NestedField(
            field_id=3, name="dataset_id", type=types.StringType(), required=True
        ),
        types.NestedField(
            field_id=4, name="job_id", type=types.StringType(), required=True
        ),
        types.NestedField(
            field_id=5, name="publish_type", type=types.StringType(), required=True
        ),
        types.NestedField(
            field_id=6, name="payload", type=types.StringType(), required=True
        ),
        types.NestedField(
            field_id=7, name="time", type=types.TimestamptzType(), required=True
        ),
    ),
}


class PUBLISH_RECORDS(IceBerg):
    def __init__(self, config):
        super().__init__(config, PUBLISH_RECORDS_SCHEMA)
