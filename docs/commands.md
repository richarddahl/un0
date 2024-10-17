# un0/db/cmd

The un0/db/cmd folder contains the following:

## create_db.py

```python
from un0.db.tools.db_tool import DBTool


if __name__ == "__main__":
    db = DBTool()
    db.drop_db()
    db.create_db()
```

## drop_db.py

```python
from un0.db.tools.db_tool import DBTool


if __name__ == "__main__":
    db = DBTool()
    db.drop_db()
```
