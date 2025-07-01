import os
import unittest

import pyarrow as pa
from deltalake import DeltaTable
from pyspark.sql import SparkSession
from servc.svc.com.storage.delta import Delta
from servc.svc.com.storage.lake import LakeTable, Medallion
from servc.svc.config import Config
from servc_typings.domains.publisher import InputSQLConfig

from src.publishers.delta import delta_publish

schema = pa.schema(
    [
        ("date", pa.string()),
        ("some_int", pa.int64()),
    ]
)

mytable: LakeTable = {
    "name": "test",
    "partitions": ["date"],
    "medallion": Medallion.BRONZE,
    "schema": schema,
}

config = {
    "database": "default",
    "catalog_name": "default",
    "catalog_properties": {
        "type": "local",
        "location": "/tmp/delta",
    },
}


class TestEngineSQL(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.table = Delta(config, mytable)
        cls.table.overwrite([])
        cls.table.insert([{"date": "2021-01-01", "some_int": 1}])
        cls.table.insert([{"date": "2021-01-02", "some_int": 1}])
        cls.table.insert([{"date": "2021-01-02", "some_int": 3}])

        cls.spark = (
            SparkSession.builder.appName("publisher")  # type: ignore
            .config("spark.driver.host", os.environ.get("POD_IP", "127.0.0.1"))
            .getOrCreate()
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.spark.stop()

    def setUp(self) -> None:
        self.deltaOptions = InputSQLConfig.model_validate(
            {
                "tablename": "test",
                "createSQL": "",
                "lakeLocation": os.path.join(
                    self.table._location_prefix, self.table._get_table_name()
                ),
                "version": self.table.getCurrentVersion() or "",
                "partitions": {},
                "partitionby": [],
            }
        )

    def test_publish_no_partition(self):
        self.deltaOptions.partitions = {
            "date": ["2022-01-01", "2022-01-02"],
        }
        _d, options = delta_publish(
            Config(),
            "my-id",
            self.deltaOptions.model_dump(),
            self.spark,
        )
        conn = DeltaTable(
            table_uri=os.path.join(
                options["path"], f"{options['database']}.{options['tablename']}"
            ),
        )

        contents = conn.to_pyarrow_table().to_pylist()
        self.assertEqual(len(contents), 0)

    def test_publish_with_data(self):
        self.deltaOptions.partitions = {
            "date": ["2021-01-02"],
        }
        _d, options = delta_publish(
            Config(),
            "my-id",
            self.deltaOptions.model_dump(),
            self.spark,
        )
        conn = DeltaTable(
            table_uri=os.path.join(
                options["path"], f"{options['database']}.{options['tablename']}"
            ),
        )

        contents = conn.to_pyarrow_table().to_pylist()
        self.assertEqual(len(contents), 2)

    def test_publish_with_partitionby(self):
        self.deltaOptions.partitionby = ["some_int"]
        _d, options = delta_publish(
            Config(),
            "my-id",
            self.deltaOptions.model_dump(),
            self.spark,
        )
        conn = DeltaTable(
            table_uri=os.path.join(
                options["path"], f"{options['database']}.{options['tablename']}"
            ),
        )

        contents = conn.to_pyarrow_table().to_pylist()
        self.assertEqual(len(contents), 3)

        partitions = conn.partitions()
        self.assertEqual(len(partitions), 2)
        self.assertIn({"some_int": "1"}, partitions)
        self.assertIn({"some_int": "3"}, partitions)


if __name__ == "__main__":
    unittest.main()
