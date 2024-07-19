from dataclasses import dataclass

import click
import duckdb

from flask import Flask, current_app, g


class ArchivalItem:
    def __init__(self, row: dict):
        self.id = row["id"]
        self.ark = row["ark"]
        self.finished = row["finished"]
        self.repository = row["repo_name"]
        self.associated_shelfmarks = row["n_unique_shelfmarks"]
        self.entries = row["n_records"]
        self.best_shelfmark = row["best_shelfmark"]
        self.old_shelfmarks = row["old_shelfmarks"]
        self.best_url = row["digitization_url"]
        self.belatedly_compiled = row["belatedly_compiled"]
        self.idno = row["idno"]
        self.collection = row["collection"]
        if row["shelfmark_hist"]:
            self.shelfmark_list = [
                {"name": k, "count": v}
                for k, v in zip(
                    row["shelfmark_hist"]["key"], row["shelfmark_hist"]["value"]
                )
            ]
        else:
            self.shelfmark_list = []
        if row["urls"]:
            self.url_list = [
                {"name": k, "count": v}
                for k, v in zip(row["urls"]["key"], row["urls"]["value"])
            ]
        else:
            self.url_list = []


@dataclass
class Citation:
    id: int
    data_id: int
    source: str
    identifier: str
    permalink: str


def get_next_id(db: duckdb.DuckDBPyConnection, table: str) -> int:
    biggest_id = db.table(table).max("id").fetchone()[0]
    if not biggest_id:
        return 1
    return biggest_id + 1


def get_all_records(
    db: duckdb.DuckDBPyConnection, condition: str = ""
) -> list[ArchivalItem]:
    rel = db.sql(f"SELECT * FROM Documents {condition}")
    row_dict = [{k: v for k, v in zip(rel.columns, r)} for r in rel.fetchall()]
    return [ArchivalItem(row) for row in row_dict]


def get_single_record(db: duckdb.DuckDBPyConnection, id: int) -> ArchivalItem:
    rel = db.sql("SELECT * FROM Documents WHERE id = {}".format(id))
    d = {k: v for k, v in zip(rel.columns, rel.fetchone())}
    return ArchivalItem(d)


def get_linked_references(
    db: duckdb.DuckDBPyConnection, id: int
) -> list[Citation] | None:
    rel = db.sql("SELECT * FROM Citations WHERE data_id = {}".format(id))
    if rel:
        l = [{k: v for k, v in zip(rel.columns, r)} for r in rel.fetchall()]
        return [Citation(**d) for d in l]


def paginate_records(
    db: duckdb.DuckDBPyConnection, offset: int, limit: int = 1, condition: str = ""
) -> list:
    rel = db.sql(
        f"SELECT * FROM Documents {condition} ORDER BY repo_name LIMIT {limit} OFFSET {offset}"
    )
    row_columns = rel.columns
    chunk = []
    for row in rel.fetchall():
        d = {k: v for k, v in zip(row_columns, row)}
        a = ArchivalItem(d)
        id = d["id"]
        refs = db.table("Citations").filter("data_id = {}".format(id))
        if refs:
            a.__setattr__("n_refs", len(refs))
        else:
            a.__setattr__("n_refs", None)
        chunk.append(a)
    return chunk


def get_db():
    """Connect to the application's configured database. The connection
    is unique for each request and will be reused if this is called
    again.
    """
    if "db" not in g:
        g.db = duckdb.connect(str(current_app.config["DATABASE"]))
        return g.db


def close_db(e=None):
    """If this request connected to the database, close the
    connection.
    """
    db = g.pop("db", None)
    if db is not None:
        db.close()


def dump_db():
    db = get_db()
    target_directory = current_app.config["DATABASE_DUMP"]
    db.execute(f"EXPORT DATABASE '{str(target_directory)}' (FORMAT PARQUET)")


def init_db_from_data():
    """Clear existing data and create new tables."""
    db = get_db()

    with current_app.open_resource("schema-from-data.sql") as f:
        sql = f.read().decode("utf8")
        try:
            db.sql(sql)
        except Exception as e:
            print(sql)
            raise e


def init_db_from_dump():
    """Clear existing data and create new tables."""
    db = get_db()

    with open(current_app.config["DATABASE_DUMP"].joinpath("schema.sql")) as f:
        sql = f.read()
        try:
            db.sql(sql)
        except Exception as e:
            print(sql)
            raise e

    with open(current_app.config["DATABASE_DUMP"].joinpath("load.sql")) as f:
        sql = f.read()
        try:
            db.sql(sql)
        except Exception as e:
            print(sql)
            raise e


@click.command("init-db-scratch")
def init_db_from_data_command():
    """Clear existing data and create new tables."""
    if current_app.config["DATABASE"].is_file():
        current_app.config["DATABASE"].unlink()
    init_db_from_data()
    click.echo("Initialized the database.")


@click.command("init-db")
def init_db_from_dump_command():
    """Clear existing data and create new tables."""
    current_app.config["DATABASE"].unlink()
    init_db_from_dump()
    click.echo("Initialized the database.")


def init_app(app: Flask):
    """Register database functions with the Flask app. This is called by
    the application factory.
    """
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_from_data_command)
    app.cli.add_command(init_db_from_dump_command)
