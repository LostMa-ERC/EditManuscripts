import duckdb
from werkzeug.exceptions import abort

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from .db import get_db, get_linked_references, get_next_id, Citation, DocumentRelation
from .record import URLParser

bp = Blueprint("references", __name__)


@bp.route("/references", methods=["GET", "POST"])
def index():
    """Show all the references."""
    url_parser = URLParser()
    db = get_db()

    record = DocumentRelation(db=db, id=url_parser.doc_id).to_dict()
    citations = get_linked_references(db=db, id=url_parser.doc_id)

    return render_template(
        "references/index.html",
        r=record,
        citations=citations,
        url_parser=url_parser,
    )


@bp.route(
    "/references/create",
    methods=["GET", "POST"],
)
def create():
    url_parser = URLParser()
    db = get_db()

    record = DocumentRelation(db=db, id=url_parser.doc_id).to_dict()
    citations = get_linked_references(db=db, id=url_parser.doc_id)

    if request.method == "POST":
        kwargs = {"source": None, "identifier": None, "permalink": None}
        for k in kwargs.keys():
            v = request.form[k]
            if v and v != "None":
                kwargs.update({k: v})
        next_id = get_next_id(db=db, table="Citations")
        kwargs.update({"id": next_id, "data_id": url_parser.doc_id})

        error = None
        if error is not None:
            flash(error)
        else:
            sql = """
INSERT INTO Citations (id, data_id, source, identifier, permalink)
VALUES ($id, $data_id, $source, $identifier, $permalink)
"""
            db.sql(query=sql, params=kwargs)
            return redirect(
                url_for(
                    "references.index",
                    id=url_parser.doc_id,
                    page=url_parser.page,
                    unfinished=url_parser.unfinished,
                )
            )

    return render_template(
        "references/create.html", r=record, citations=citations, url_parser=url_parser
    )


@bp.route(
    "/references/delete",
    methods=("POST", "GET"),
)
def delete():
    """Delete a reference."""

    url_parser = URLParser()
    db = get_db()
    sql = f"DELETE FROM Citations WHERE id = {url_parser.ref_id}"
    db.sql(sql)
    return redirect(
        url_for(
            "references.index",
            id=url_parser.doc_id,
            page=url_parser.page,
            unfinished=url_parser.unfinished,
        )
    )
