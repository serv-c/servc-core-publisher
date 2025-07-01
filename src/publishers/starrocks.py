import os
from typing import Any, Dict, Tuple
from urllib.parse import urlparse

from pydantic import ValidationError
from servc.svc.config import Config
from servc.svc.io.output import InvalidInputsException
from servc_typings.com.db import Database
from servc_typings.domains.data import DatabaseConfig
from servc_typings.domains.publisher import SQLOptions

from src.lib.readdf import tableConfigtoDf

MYSQL_URL = os.getenv("MYSQL_URL", "mysql://root@localhost:9030")


def starrocks_publish(
    c: Config, dataset_id: str, rawoptions: Any, spark
) -> Tuple[str, Dict[str, Any]]:
    try:
        options = SQLOptions.model_validate(rawoptions)
    except ValidationError as e:
        raise InvalidInputsException(str(e))

    # get the server connection information
    config = Config()
    config.setValue("url", MYSQL_URL.replace("mysql://", "mysql+mysqlconnector://"))
    config.setValue("dbtype", "mysql")
    db = Database(config)
    parsed_uri = urlparse(MYSQL_URL)

    # get the database configuratio and create the database
    db.query(
        f"CREATE DATABASE IF NOT EXISTS {dataset_id}", return_rows=False, commit=True
    )
    db.close()
    config.setValue("url", "/".join([config.get("url"), dataset_id]))
    db = Database(config)

    overall_sql = options.sql

    # for each table, create the table if it does not exist
    # and write the data to the table
    for input_table in options.inputTables:
        if input_table.tablename not in input_table.createSQL:
            raise InvalidInputsException(
                f"Input table {input_table.tablename} is missing the 'tablename' field."
            )
        tablename = ".".join([dataset_id, input_table.tablename + "_temp"])
        sql = input_table.createSQL.replace(
            f" {input_table.tablename} ", f" {tablename} "
        )

        db.query(f"DROP TABLE IF EXISTS {tablename}", return_rows=False, commit=True)
        db.query(sql, return_rows=False, commit=True, dialect="mysql")

        # overall_sql = overall_sql.replace(input_table.tablename, new_tablename)

        try:
            df = tableConfigtoDf(input_table, spark)

            if os.environ.get("TEST_ENV", "false").lower() == "true":
                df.write.format("jdbc").options(
                    url=f"jdbc:mysql://{parsed_uri.hostname}:{parsed_uri.port}",
                    driver="com.mysql.cj.jdbc.Driver",
                    dbtable=tablename,
                    user=parsed_uri.username or "root",
                ).mode("append").save()
            else:
                df.write.format("starrocks").option(
                    "starrocks.fe.http.url", f"{parsed_uri.hostname}:8030"
                ).option(
                    "starrocks.fe.jdbc.url", f"jdbc:mysql://{parsed_uri.hostname}:9030"
                ).option(
                    "starrocks.table.identifier", tablename
                ).option(
                    "starrocks.user", "root"
                ).option(
                    "starrocks.password", ""
                ).mode(
                    "append"
                ).save()

        except InvalidInputsException as e:
            pass
            # raise InvalidInputsException(
            #     f"Failed to write data for table {input_table.tablename}: {str(e)}"
            # )

    # rename the temporary database to the dataset_id
    for input_table in options.inputTables:
        temp_tablename = input_table.tablename + "_temp"
        new_tablename = input_table.tablename
        db.query(
            f"DROP TABLE IF EXISTS {new_tablename}", return_rows=False, commit=True
        )
        db.query(
            f"ALTER TABLE {temp_tablename} RENAME {new_tablename}",
            return_rows=False,
            commit=True,
            dialect="mysql",
        )

    return (
        "database",
        DatabaseConfig.model_validate(
            {
                "url": "/".join([MYSQL_URL, dataset_id]),
                "sql": overall_sql,
                "dialect": "mysql",
            }
        ).model_dump(),
    )
