import json
import os
import unittest

import pyarrow as pa
from servc.svc.com.storage.delta import Delta
from servc.svc.com.storage.lake import LakeTable, Medallion
from servc.svc.config import Config
from servc.svc.io.output import InvalidInputsException
from servc_typings.com.db import Database
from servc_typings.domains.publisher import PublishOptions
from servc_typings.tables.publish_record import PUBLISH_RECORDS

from src.domains.publish import publish
from tests import init_db

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

deltaconfig = {
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
        init_db()
        cls.table = Delta(deltaconfig, mytable)
        cls.table.overwrite([])
        cls.table.insert([{"date": "2021-01-01", "some_int": 1}])
        cls.table.insert([{"date": "2021-01-02", "some_int": 1}])
        cls.table.insert([{"date": "2021-01-02", "some_int": 3}])

        config = Config()
        cls.database = Database(config.get(f"conf.{Database.name}"))
        cls.records = PUBLISH_RECORDS(config.get(f"conf.{PUBLISH_RECORDS.name}"))
        cls.context = {
            "config": config,
            "middlewares": [cls.database, cls.records],
        }

    @classmethod
    def tearDownClass(cls) -> None:
        cls.database.close()

    def setUp(self) -> None:
        self.database.query("DELETE FROM datasets", return_rows=False, commit=True)
        self.records.overwrite([])
        self.raw_payload = {
            "app_id": "chess",
            "tenant_name": "test_tenant",
            "job_id": "test_job",
            "type": "delta",
            "options": {
                "tablename": "test",
                "createSQL": "",
                "lakeLocation": os.path.join(
                    self.table._location_prefix, self.table._get_table_name()
                ),
                "version": self.table.getCurrentVersion() or "",
                "partitions": {},
                "partitionby": [],
            },
            "sparkConfig": {},
        }
        self.payload = PublishOptions.model_validate(self.raw_payload)

    def test_publish_no_partition(self):
        publish("", self.payload.model_dump(), self.context)

        # validate the dataset was created
        dataset_id = self.database.query(
            "SELECT dataset_id FROM datasets WHERE app_id = :app_id AND auth_expression = :tenant_name",
            {"app_id": self.payload.app_id, "tenant_name": self.payload.tenant_name},
        )[0]["dataset_id"]
        self.assertIsNotNone(dataset_id)

        # validate the publishing record was created
        records = self.records.read(["*"]).to_pylist()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["dataset_id"], dataset_id)
        self.assertEqual(records[0]["app_id"], self.payload.app_id)
        self.assertEqual(records[0]["payload"], json.dumps(self.raw_payload))

    def test_multiple_publishing(self):
        publish("", self.payload.model_dump(), self.context)
        self.assertRaises(
            InvalidInputsException,
            lambda: publish("", self.payload.model_dump(), self.context),
        )
        rows = self.database.query("SELECT * FROM datasets")
        self.assertEqual(len(rows), 1)

        records = self.records.read(["*"]).to_pylist()
        self.assertEqual(len(records), 1)

    def test_multiple_job_publishing(self):
        publish("", self.payload.model_dump(), self.context)

        self.payload.job_id = "test_job_2"
        publish("", self.payload.model_dump(), self.context)
        rows = self.database.query("SELECT * FROM datasets")
        self.assertEqual(len(rows), 1)

        records = self.records.read(["*"]).to_pylist()
        self.assertEqual(len(records), 2)

    def test_publish_with_failure(self):
        raw_options = {
            "app_id": "chess",
            "tenant_name": "test_tenant",
            "job_id": "test_job",
            "type": "database",
            "sparkConfig": {},
            "options": {
                "sparkConfig": {},
                "sql": "SELECT * FROM test",
                "inputTables": [
                    {
                        "tablename": "test",
                        "createSQL": "CREATE TABLE test (date STRING, some_int int) ORDER BY (some_int)",
                        "lakeLocation": os.path.join(
                            self.table._location_prefix, self.table._get_table_name()
                        ),
                        "version": self.table.getCurrentVersion() or "",
                        "partitions": {},
                        "partitionby": [],
                    },
                ],
            },
        }
        publish("", raw_options, self.context)
        details = json.loads(
            self.database.query("SELECT details FROM datasets")[0]["details"]
        )["url"]

        dbconfig = Config()
        dbconfig.setValue("url", details.replace("mysql://", "mysql+mysqlconnector://"))
        dbconfig.setValue("dbtype", "mysql")
        db = Database(dbconfig)
        rows = db.query("SELECT * FROM test")
        databases = len(db.query("SHOW DATABASES"))

        # run a bad job
        raw_options["job_id"] = "test_job_2"
        raw_options["options"]["inputTables"][0][
            "createSQL"
        ] = "CREATEas_int int) ORDER BY (some3_int)"
        self.assertRaises(
            InvalidInputsException,
            lambda: publish("", raw_options, self.context),
        )

        # validate the dataset was not lost and a new database was not created
        self.assertEqual(len(rows), len(db.query("SELECT * FROM test")))
        self.assertEqual(databases, len(db.query("SHOW DATABASES")))


if __name__ == "__main__":
    unittest.main()
