from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel


class PublishType(Enum):
    WAREHOUSE = "database"
    DELTA = "delta"


class InputSQLConfig(BaseModel):
    tablename: str
    createSQL: str
    lakeLocation: str
    partitions: Dict[str, List[str]]
    version: str
    partitionby: List[str]


class SQLOptions(BaseModel):
    sql: str
    inputTables: List[InputSQLConfig]


class PublishOptions(BaseModel):
    app_id: str
    tenant_name: str
    job_id: str
    type: str
    options: Dict[str, Any]
    sparkConfig: Dict[str, str]
