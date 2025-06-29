import os
from typing import Any, Dict, Tuple

from pydantic import ValidationError
from servc.svc.config import Config
from servc.svc.io.output import InvalidInputsException
from servc_typings.domains.data import DeltaConfig

from src.lib.readdf import tableConfigtoDf
from src.pyetl import InputSQLConfig


def delta_publish(
    c: Config, dataset_id: str, rawoptions: Any, spark
) -> Tuple[str, Dict[str, Any]]:
    try:
        options = InputSQLConfig.model_validate(rawoptions)
    except ValidationError as e:
        raise InvalidInputsException(str(e))

    # read table into dataframe
    df = tableConfigtoDf(options, spark)
    deltaconfig = DeltaConfig.model_validate(
        {
            "database": dataset_id,
            "path": os.path.join(
                os.path.dirname(options.lakeLocation),
                "published",
            ),
            "tablename": options.tablename,
        }
    )

    new_table_path = os.path.join(
        deltaconfig.path,
        ".".join([deltaconfig.database, deltaconfig.tablename]),
    )

    df.write.format("delta").partitionBy(*options.partitionby).option(
        "overwriteSchema", "true"
    ).mode("overwrite").save(new_table_path.replace("s3://", "s3a://"))

    return ("delta", deltaconfig.model_dump())
