# EditManuscripts

Local web application for ergonomically editing bibliographic details about manuscripts (Archival Items) in the database.

```console
flask --app app run
```

![home page](img/homepage.png)

1. Edit details about the Archival Item.

![edit archival item](img/edit_archival_item.png)

2. Add and delete bibliographic references to the Archival Item in external databases, i.e. Biblissima.

![add new reference](img/add_reference.png)
![edit reference](img/edited_reference.png)

## Set up

1. Git clone this repository.

```console
git clone git@github.com:LostMa-ERC/EditManuscripts.git
cd EditManuscripts
```

2. In a virtual Python environment (v. 3.12), install the requirements.

```console
pip install -r requirements.txt
```

3. Initialize the database.

    - If you're starting from scratch, (a) load the CSV data you need in the [`./data`](data/) folder and (b) use the SQL script in [`schema-from-data.sql`](app/schema-from-data.sql).

    ```console
    flask --app app init-db-scratch
    ```

    - You can re-initiate the database from a version that you dumped from within the web application, which is initially saved to the instance of the web application's `./instance folder`.

    ```console
    flask --app app init-db
    ```

4. Run the web application and start editing.

```console
flask --app app run
```
