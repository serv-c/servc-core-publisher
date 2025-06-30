from typing import List

QUERIES: List[str] = [
    "DROP TABLE IF EXISTS datasets;",
    """
    CREATE TABLE datasets (
        dataset_id varchar,
        app_id varchar,
        auth_expression varchar,
        location_type varchar,
        details varchar
    );
    """,
    "DROP TABLE IF EXISTS apps",
    """
    CREATE TABLE IF NOT EXISTS apps (
        app_id character varying(255) NOT NULL,
        name character varying(255) NOT NULL,
        url character varying(255) NOT NULL,
        login_url character varying(255) NOT NULL,
        auth_expression character varying(255) NOT NULL
    );
    """,
    """
    INSERT INTO "apps"("app_id","name","url","login_url","auth_expression")
    VALUES
      ('servc','Serv-C','https://servc.io','https://servc.io/login','${user_id}'),
      ('chess','chess','https://chess.servc.io/','https://chess.servc.io/login','${user_id}');
    """,
    "DROP TABLE IF EXISTS users",
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id character varying(255) NOT NULL,
        email character varying(255) NOT NULL,
        name character varying(255) NOT NULL,
        last_login character varying(255) NOT NULL
    );
    """,
    """
    INSERT INTO "users"("user_id","email","name","last_login")
    VALUES
      ('test_user','test@example.org','Test User','2025-05-20 23:07:45.599656+00'),
      ('yusuf','ali@yusuf.email','Yusuf Ali','2025-05-20 23:07:45.599656+00'),
      ('yusuf','y6ali@uwaterloo.ca','Yusuf Ali','2025-05-21 03:41:58.535582+00');
    """,
    "DROP TABLE IF EXISTS perms",
    """
    CREATE TABLE IF NOT EXISTS perms (
        app_id character varying(255) NOT NULL,
        user_id character varying(255) NOT NULL,
        auth_expression character varying(255) NOT NULL,
        resource character varying(255),
        verb character varying(255)
    );
    """,
    """
    INSERT INTO "perms"("app_id","user_id","auth_expression","resource","verb")
    VALUES
    ('chess','yusuf','yusuf','spec','r'),
    ('chess','yusuf','user2','dataset','r'),
    ('chess','yusuf','yusuf','dataset','r');
        """,
    # data sets
    """
    DROP TABLE IF EXISTS datasets
    """,
    """
    CREATE TABLE datasets (
      dataset_id character varying(255) NOT NULL UNIQUE,
      app_id character varying(255) NOT NULL,
      auth_expression character varying(255) NOT NULL,
      location_type character varying(15) NOT NULL,
      details text NOT NULL
    );
    """,
]
