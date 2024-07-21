from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from .db import DocumentRelation, get_db, dump_db

bp = Blueprint("record", __name__)


class URLParser:
    def __init__(self):
        self.page = request.args.get("page", 1, type=int)
        self.unfinished = request.args.get("unfinished", 0, type=int)
        self.doc_id = request.args.get("id", 0, type=int)
        self.city = request.args.get("city", 0, type=int)
        self.ref_id = request.args.get("ref_id", 0, type=int)
        self._next_url = url_for(
            "record.index",
            unfinished=self.unfinished,
            page=self.page + 1,
            city=self.city,
        )

    @property
    def prev_url(self) -> str:
        if self.page == 1:
            return None
        else:
            return url_for(
                "record.index",
                unfinished=self.unfinished,
                page=self.page - 1,
                city=self.city,
            )

    @property
    def next_url(self) -> str:
        return self._next_url

    @next_url.setter
    def next_url(self, value):
        self._next_url = value

    @property
    def current_url(self) -> str:
        return url_for(
            "record.index", unfinished=self.unfinished, page=self.page, city=self.city
        )

    @property
    def offset(self) -> int:
        if self.page == 1:
            return 0
        else:
            return self.page - 1

    @property
    def all_docs_url(self) -> str:
        return url_for("record.index", page=None, unfinished=0, city=self.city)

    @property
    def unfinished_url(self) -> str:
        return url_for("record.index", page=None, unfinished=1, city=self.city)


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
    url_parser = URLParser()
    offset = url_parser.offset

    db = get_db()
    rel = DocumentRelation(
        db=db, city=url_parser.city, unfinished=url_parser.unfinished
    )
    cities = rel.cities
    current_city_label = None
    if url_parser.city and url_parser.city != 0:
        current_city_label = f"{rel.city_dict[url_parser.city]["name"]}"

    total_finished = rel.total_finished
    total_to_do = rel.total_to_do
    total_all = rel.total_rows

    chunk = rel.get_chunk(unfinished=url_parser.unfinished, offset=offset)
    records = rel.to_dict(chunk)
    if not isinstance(records, list):
        records = []

    if url_parser.page + 1 > total_to_do:
        url_parser.next_url = None

    if request.method == "POST":
        city = request.form["city"]
        return redirect(
            url_for(
                "record.index",
                page=url_parser.page,
                unfinished=url_parser.unfinished,
                city=city,
                city_label=current_city_label,
            )
        )

    return render_template(
        "record/index.html",
        records=records,
        url_parser=url_parser,
        cities=cities,
        city_label=current_city_label,
        total_to_do=total_to_do,
        total_all=total_all,
        total_finished=total_finished,
    )


@bp.route("/update", methods=("GET", "POST"))
def update():
    """Update a record."""

    url_parser = URLParser()

    db = get_db()
    rel = DocumentRelation(db=db, id=url_parser.doc_id)
    record = rel.to_dict()

    if request.method == "POST":

        kwargs = {
            "best_shelfmark": None,
            "collection": None,
            "best_url": None,
            "secondary_digitization": None,
            "old_shelfmarks": None,
            "ark": None,
            "catalogue_entry": None,
            "belatedly_compiled": None,
        }
        for k in kwargs.keys():
            v = request.form[k]
            if v and v != "None":
                kwargs.update({k: v})
        kwargs.update({"id": url_parser.doc_id})

        error = None
        if error is not None:
            flash(error)

        else:
            sql = """
UPDATE Documents
SET
    best_shelfmark = $best_shelfmark, 
    collection = $collection, 
    best_url = $best_url, 
    secondary_digitization = $secondary_digitization, 
    old_shelfmarks = $old_shelfmarks, 
    ark = $ark,
    catalogue_entry = $catalogue_entry, 
    belatedly_compiled = $belatedly_compiled, 
    finished = True
WHERE id = $id
"""
            db.sql(query=sql, params=kwargs)
            return redirect(
                url_for(
                    "record.index",
                    page=url_parser.page,
                    unfinished=url_parser.unfinished,
                    city=url_parser.city,
                )
            )

    return render_template(
        "record/update.html",
        r=record,
        url_parser=url_parser,
    )


@bp.route(
    "/record/undo_approval",
    methods=("POST", "GET"),
)
def undo_approval():
    """Undo the finished value of a record."""

    url_parser = URLParser()
    db = get_db()
    sql = f"""
UPDATE Documents
SET finished = False
WHERE id = {url_parser.doc_id}
"""
    db.sql(sql)
    return redirect(
                url_for(
                    "record.index",
                    page=url_parser.page,
                    unfinished=url_parser.unfinished,
                    city=url_parser.city,
                )
            )
