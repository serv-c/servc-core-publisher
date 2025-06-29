import os
import unittest

import pyarrow as pa
from pyspark.sql import SparkSession
from servc.svc.com.storage.delta import Delta
from servc.svc.com.storage.lake import LakeTable, Medallion
from servc.svc.config import Config
from servc_typings.com.db import Database

from src.publishers.starrocks import starrocks_publish as publish
from src.pyetl import SQLOptions

schema = pa.schema(
    [
        ("date", pa.string()),
        ("some_int", pa.int64()),
    ]
)

schema2 = pa.schema(
    [
        ("lol", pa.string()),
        ("some_int", pa.int64()),
    ]
)

mytable: LakeTable = {
    "name": "test",
    "partitions": ["date"],
    "medallion": Medallion.BRONZE,
    "schema": schema,
}

mytable2: LakeTable = {
    "name": "test2",
    "partitions": ["some_int"],
    "medallion": Medallion.SILVER,
    "schema": schema2,
}

config = {
    "database": "default",
    "catalog_name": "default",
    "catalog_properties": {
        "type": "local",
        "location": "/tmp/delta",
    },
}

MYSQL_URL = os.getenv("MYSQL_URL", "mysql://root@localhost:9030")


class TestStarRocks(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.table = Delta(config, mytable)
        cls.table.overwrite([])
        cls.table.insert([{"date": "2021-01-01", "some_int": 1}])
        cls.table.insert([{"date": "2021-01-02", "some_int": 1}])
        cls.table.insert([{"date": "2021-01-02", "some_int": 3}])

        cls.table2 = Delta(config, mytable2)
        cls.table2.overwrite([])
        cls.table2.insert([{"lol": "2021-01-01", "some_int": 1}])
        cls.table2.insert([{"lol": "2021-01-02", "some_int": 1}])
        cls.table2.insert([{"lol": "2021-01-02", "some_int": 3}])

        cls.spark = (
            SparkSession.builder.appName("publisher")  # type: ignore
            .config("spark.driver.host", os.environ.get("POD_IP", "127.0.0.1"))
            .getOrCreate()
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.spark.stop()

    def setUp(self) -> None:
        self.raw_options = {
            "sql": "SELECT * FROM test INNER JOIN test2 ON test.some_int = test2.some_int",
            "inputTables": [
                {
                    "tablename": "test",
                    "createSQL": "CREATE TABLE test (date STRING, some_int int) ORDER BY (date)",
                    "lakeLocation": os.path.join(
                        self.table._location_prefix, self.table._get_table_name()
                    ),
                    "version": self.table.getCurrentVersion() or "",
                    "partitions": {},
                    "partitionby": [],
                },
                {
                    "tablename": "test2",
                    "createSQL": "CREATE TABLE test2 (lol STRING, some_int int) ORDER BY (some_int)",
                    "lakeLocation": os.path.join(
                        self.table2._location_prefix, self.table2._get_table_name()
                    ),
                    "version": self.table2.getCurrentVersion() or "",
                    "partitions": {},
                    "partitionby": [],
                },
            ],
        }
        self.options = SQLOptions.model_validate(self.raw_options)

    def test_publish(self):
        _d, options = publish(
            Config(),
            "my_id",
            self.options.model_dump(),
            self.spark,
        )

        dbconfig = Config()
        dbconfig.setValue(
            "url", options["url"].replace("mysql://", "mysql+mysqlconnector://")
        )
        dbconfig.setValue("dbtype", "mysql")
        db = Database(dbconfig)

        contents = db.query(options["sql"])
        table2 = db.query("SELECT * FROM test2")
        db.close()

        self.assertEqual(len(contents), 5)
        self.assertEqual(len(table2), 3)

    def test_publish_with_partition(self):
        self.raw_options["inputTables"][1]["partitions"] = {"some_int": ["3"]}
        self.options = SQLOptions.model_validate(self.raw_options)

        _d, options = publish(
            Config(),
            "my_id",
            self.options.model_dump(),
            self.spark,
        )

        dbconfig = Config()
        dbconfig.setValue(
            "url", options["url"].replace("mysql://", "mysql+mysqlconnector://")
        )
        dbconfig.setValue("dbtype", "mysql")
        db = Database(dbconfig)

        contents = db.query(options["sql"])
        table2 = db.query("SELECT * FROM test2")
        db.close()

        self.assertEqual(len(contents), 1)
        self.assertEqual(len(table2), 1)


if __name__ == "__main__":
    unittest.main()
