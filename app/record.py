from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from .db import get_all_records, get_db, dump_db, get_single_record, paginate_records

bp = Blueprint("record", __name__)


@bp.route("/", methods=["GET", "POST"])
def home():
    return redirect(url_for("record.index", unfinished=0))


@bp.route("/dump", methods=["GET", "POST"])
def dump():
    dump_db()
    return redirect(url_for("record.index", unfinished=0))


@bp.route("/index", methods=["GET", "POST"])
def index():
    """Show all the records."""
    page = request.args.get("page", 1, type=int)
    only_unfinished = request.args.get("unfinished", 0, type=int)

    if page == 1:
        prev_url = None
        offset = 0
        next_url = url_for("record.index", unfinished=only_unfinished, page=page + 1)
    else:
        prev_url = url_for("record.index", unfinished=only_unfinished, page=page - 1)
        offset = page - 1
        next_url = url_for("record.index", unfinished=only_unfinished, page=page + 1)

    db = get_db()

    total_finished = len(get_all_records(db, condition="WHERE finished IS TRUE"))
    total_all = len(get_all_records(db))

    all_url = url_for("record.index", page=None, unfinished=0)
    unfinished_url = url_for("record.index", page=None, unfinished=1)

    if only_unfinished and only_unfinished == 1:
        condition = "WHERE NOT finished"
        total = total_all - total_finished
    else:
        condition = ""
        total = total_all

    current_chunk = paginate_records(db=db, offset=offset, condition=condition)

    db.close()

    return render_template(
        "record/index.html",
        records=current_chunk,
        next_url=next_url,
        prev_url=prev_url,
        total=total,
        current=page,
        all_url=all_url,
        page=page,
        unfinished=only_unfinished,
        unfinished_url=unfinished_url,
        total_all=total_all,
        total_finished=total_finished,
    )


@bp.route("/<int:unfinished>/<int:page>/<int:id>/update", methods=("GET", "POST"))
def update(id, page, unfinished):
    """Update a record."""
    if page == 1:
        prev_url = None
        next_url = url_for("record.index", unfinished=unfinished, page=page + 1)
    else:
        prev_url = url_for("record.index", unfinished=unfinished, page=page - 1)
        next_url = url_for("record.index", unfinished=unfinished, page=page + 1)
    current_url = url_for("record.index", unfinished=unfinished, page=page)

    db = get_db()

    record = get_single_record(db, id)

    if request.method == "POST":
        best_shelfmark = request.form["best_shelfmark"]
        if best_shelfmark == "None":
            best_shelfmark = None
        collection = request.form["collection"]
        if collection == "None":
            collection = None
        digitization_url = request.form["digitization_url"]
        if digitization_url == "None":
            digitization_url = None
        old_shelfmarks = request.form["old_shelfmarks"]
        if old_shelfmarks == "None":
            old_shelfmarks = None
        ark = request.form["ark"]
        if ark == "None":
            ark = None
        belatedly_compiled = request.form["belatedly_compiled"]
        if belatedly_compiled == "None":
            belatedly_compiled = None
        error = None

        if error is not None:
            flash(error)
        else:
            sql = """
UPDATE Documents
SET best_shelfmark = ?, collection = ?, digitization_url = ?, old_shelfmarks = ?, ark = ?, belatedly_compiled = ?, finished = True
WHERE id = ?
"""
            db.sql(
                query=sql,
                params=(
                    best_shelfmark,
                    collection,
                    digitization_url,
                    old_shelfmarks,
                    ark,
                    belatedly_compiled,
                    id,
                ),
            )
            return redirect(url_for("record.index", page=page, unfinished=unfinished))

    return render_template(
        "record/update.html",
        r=record,
        page=page,
        unfinished=unfinished,
        prev_url=prev_url,
        next_url=next_url,
        current_url=current_url,
    )
