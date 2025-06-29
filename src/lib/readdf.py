from typing import Any

from src.pyetl import InputSQLConfig


def tableConfigtoDf(options: InputSQLConfig, spark: Any):
    df = (
        spark.read.format("delta")
        .option("versionAsOf", int(options.version))
        .load(options.lakeLocation.replace("s3://", "s3a://"))
    )
    for columnname, values in options.partitions.items():
        df = df.filter(df[columnname].isin(values))

    return df
