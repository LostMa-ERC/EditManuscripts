DROP TABLE IF EXISTS Citations;

DROP TABLE IF EXISTS Documents;

CREATE TABLE Documents(
	id INTEGER PRIMARY KEY,
	finished BOOLEAN DEFAULT False,
	repo_name VARCHAR,
	repo_id VARCHAR,
	n_unique_shelfmarks INTEGER,
	n_records INTEGER,
	shelfmark_hist MAP(VARCHAR, UBIGINT),
	best_shelfmark VARCHAR,
	old_shelfmarks VARCHAR,
	digitization_url VARCHAR,
	belatedly_compiled BOOLEAN,
	idno VARCHAR,
	ark VARCHAR,
	collection VARCHAR,
	row_ids VARCHAR[],
	urls MAP(VARCHAR, UBIGINT),
	n_false INTEGER,
	n_true INTEGER
);

CREATE SEQUENCE IF NOT EXISTS id_sequence START 1;

INSERT INTO Documents
	(id,
	repo_name,
	repo_id,
	n_unique_shelfmarks,
	n_records,
	shelfmark_hist,
	best_shelfmark,
	digitization_url,
	idno,
	collection,
	row_ids,
	urls,
	n_false,
	n_true
	)
SELECT 
	nextval('id_sequence'),
	any_value("institutional name"), 
	"repository H-ID", 
	count(distinct(Shelfmark)), 
	count(row_id), 
	histogram(Shelfmark), 
	case when count(distinct(Shelfmark)) = 1 then any_value(Shelfmark) ELSE NULL END,
	case when count(distinct(Digitisation)) = 1 and any_value(Digitisation) LIKE 'http%' THEN any_value(Digitisation) ELSE NULL END,
	idno, 
	any_value(collection),
	list(row_id), 
	histogram(Digitisation),
	sum(case when ToCheck like 'False' then 1 else 0 end), 
	sum(case when ToCheck like 'True' then 1 else 0 end)
FROM (
	SELECT r."institutional name", crm."repository H-ID", cf.Shelfmark , cf.repository, cf.idno, cf.row_id, cf.ToCheck, cf.Digitisation, cf.collection
	FROM 'data/corpus_revu.csv' cf
	LEFT JOIN 'data/corpus_repo_mapping.csv' crm 
		ON cf.Settlement = crm.orig_Settlement 
		AND cf.repository = crm.orig_repository 
	LEFT JOIN 'data/repositories_export.csv' r
		ON r."repository H-ID" = crm."repository H-ID"
	WHERE r."repository H-ID" is not null
)
GROUP BY "repository H-ID", repository, idno
HAVING count(*) > 1
ORDER BY count(*) desc;

DROP SEQUENCE id_sequence;

CREATE SEQUENCE id_sequence START 1;

DROP TABLE IF EXISTS Citations;

CREATE TABLE Citations (
	id INTEGER DEFAULT nextval('id_sequence') PRIMARY KEY,
	data_id INTEGER,
	source VARCHAR,
	identifier VARCHAR,
	permalink VARCHAR,
	FOREIGN KEY (data_id) REFERENCES Documents(id)
);
