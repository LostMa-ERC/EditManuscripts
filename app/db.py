from dataclasses import dataclass

import click
import duckdb

from flask import Flask, current_app, g


def count_linked_references(db: duckdb.DuckDBPyConnection, id: int) -> int:
    rel = db.sql(f"SELECT * FROM Citations WHERE data_id = {id}")
    return rel.count("*").fetchone()[0]


class Doc:
    def __init__(self, row: dict):
        self.id = row["id"]
        self.ark = row["ark"]
        self.catalogue_entry = row["catalogue_entry"]
        self.finished = row["finished"]
        self.repository = row["repository"]
        self.city = row["city"]
        self.city_id = row["city_id"]
        self.country = row["country"]
        self.titles = row["titles"]
        self.associated_shelfmarks = row["associated_shelfmarks"]
        self.entries = row["entries"]
        self.best_shelfmark = row["best_shelfmark"]
        self.old_shelfmarks = row["old_shelfmarks"]
        self.best_url = row["best_url"]
        self.secondary_digitization = row["secondary_digitization"]
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


class DocumentRelation:
    def __init__(
        self,
        db: duckdb.DuckDBPyConnection,
        id: int | None = None,
        city: int | None = None,
        unfinished: int | None = None,
    ):
        self.conn = db
        self.total_rows = self.conn.table("Documents").count("*").fetchone()[0]
        self.total_finished = (
            self.conn.table("Documents").filter("finished").count("*").fetchone()[0]
        )

        if id and id != 0:
            self.base = (
                self.conn.table("Documents").order("country, city").filter(f"id = {id}")
            )
        elif city and city != 0:
            self.base = (
                self.conn.table("Documents")
                .order("country, city")
                .filter(f"city_id = {city}")
            )
        else:
            self.base = self.conn.table("Documents").order("country, city")

        if unfinished and unfinished == 1:
            self.total_to_do = self.base.filter("NOT finished").count("*").fetchone()[0]
        else:
            self.total_to_do = self.base.count("*").fetchone()[0]

    @property
    def all(self) -> duckdb.DuckDBPyRelation:
        return self.base

    @property
    def unfinished(self) -> duckdb.DuckDBPyRelation:
        return self.base.filter("NOT finished")

    @property
    def finished(self) -> duckdb.DuckDBPyRelation:
        rel = self.base.filter("finished")
        return rel

    def get_chunk(
        self, unfinished: int, offset: int, limit: int = 1
    ) -> duckdb.DuckDBPyRelation:
        if unfinished and unfinished == 1:
            rel = self.base.filter("NOT finished")
        else:
            rel = self.base
        return rel.limit(limit, offset=offset)

    @classmethod
    def count(cls, base: duckdb.DuckDBPyRelation) -> int:
        return base.count("*").fetchone()[0]

    def to_dict(self, rel: duckdb.DuckDBPyRelation | None = None) -> Doc | list[Doc]:
        if rel:
            l = []
            for row in rel.fetchall():
                d = Doc({k: v for k, v in zip(rel.columns, row)})
                n_refs = count_linked_references(db=self.conn, id=d.id)
                d.__setattr__("n_refs", n_refs)
                l.append(d)
            return l
        else:
            rel = self.base
            d = Doc({k: v for k, v in zip(rel.columns, rel.fetchone())})
            n_refs = count_linked_references(db=self.conn, id=d.id)
            d.__setattr__("n_refs", n_refs)
            return d


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


def get_linked_references(
    db: duckdb.DuckDBPyConnection, id: int
) -> list[Citation] | None:
    rel = db.sql(f"SELECT * FROM Citations WHERE data_id = {id}")
    if rel:
        l = [{k: v for k, v in zip(rel.columns, r)} for r in rel.fetchall()]
        return [Citation(**d) for d in l]


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
