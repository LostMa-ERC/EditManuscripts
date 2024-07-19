import duckdb
from werkzeug.exceptions import abort

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from .db import (
    get_db,
    ArchivalItem,
    get_all_records,
    get_single_record,
    get_linked_references,
    get_next_id,
    Citation,
)

bp = Blueprint("references", __name__)


@bp.route(
    "/<int:unfinished>/<int:page>/record=<int:id>/references", methods=["GET", "POST"]
)
def index(id, page, unfinished):
    """Show all the references."""
    if page == 1:
        prev_url = None
        next_url = url_for("record.index", unfinished=unfinished, page=page + 1)
    else:
        prev_url = url_for("record.index", unfinished=unfinished, page=page - 1)
        next_url = url_for("record.index", unfinished=unfinished, page=page + 1)
    current_url = url_for("record.index", unfinished=unfinished, page=page)

    db = get_db()

    record = get_single_record(db, id)
    citations = get_linked_references(db=db, id=id)

    return render_template(
        "references/index.html",
        r=record,
        citations=citations,
        unfinished=unfinished,
        page=page,
        prev_url=prev_url,
        next_url=next_url,
        current_url=current_url,
    )


@bp.route(
    "/<int:unfinished>/<int:page>/record=<int:id>/references/create",
    methods=["GET", "POST"],
)
def create(id, page, unfinished):
    if page == 1:
        prev_url = None
        next_url = url_for("record.index", unfinished=unfinished, page=page + 1)
    else:
        prev_url = url_for("record.index", unfinished=unfinished, page=page - 1)
        next_url = url_for("record.index", unfinished=unfinished, page=page + 1)
    current_url = url_for("record.index", unfinished=unfinished, page=page)

    db = get_db()

    record = get_single_record(db, id)
    citations = get_linked_references(db=db, id=id)

    if request.method == "POST":
        source = request.form["source"]
        if source == "None":
            source = None
        else:
            source = source.lower().strip()

        identifier = request.form["identifier"]
        if identifier == "None":
            identifier = None
        else:
            identifier = identifier.strip()

        permalink = request.form["permalink"]
        if permalink == "None":
            permalink = None
        else:
            permalink = permalink.strip()

        error = None

        if error is not None:
            flash(error)
        else:
            next_id = get_next_id(db=db, table="Citations")
            sql = """
INSERT INTO Citations (id, data_id, source, identifier, permalink)
VALUES (?, ?, ?, ?, ?)
"""
            db.sql(query=sql, params=(next_id, id, source, identifier, permalink))
            return redirect(
                url_for("references.index", id=id, page=page, unfinished=unfinished)
            )

    return render_template(
        "references/create.html",
        r=record,
        citations=citations,
        id=id,
        unfinished=unfinished,
        page=page,
        prev_url=prev_url,
        next_url=next_url,
        current_url=current_url,
    )


@bp.route(
    "/<int:unfinished>/<int:page>/record=<int:rec_id>/reference=<int:ref_id>/delete",
    methods=("POST", "GET"),
)
def delete(unfinished, page, rec_id, ref_id):
    """Delete a reference."""
    print("WENT TO DELETE PAGE!!!!")

    db = get_db()

    sql = f"DELETE FROM Citations WHERE id = {ref_id}"
    print(sql)
    db.sql(sql)

    return redirect(
        url_for("references.index", id=rec_id, page=page, unfinished=unfinished)
    )
