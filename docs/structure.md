# File Structure and Code Style

## File Structure

un0 has (what I think is) a typical python library "src" structure

    un0
    | docs
    | src
      | un0
        | attr
        | auth
        | cmd
        | db
        | fltr
        | msg
        | rltd
        | rprt
        | wkflw
    | Tests

### App Modules

Each module within un0 that provides database tables and associated functionailty is considered an app module.

App modules generally contain the following files:

- enums.py: Contains enums used as values in the database
- models.py: Contains the UN0Model objects for the database tables
- tables.py:  Contains the sqlalchemy DeclarativeBase tables

## Code Style
