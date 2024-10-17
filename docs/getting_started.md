## Major Dependencies
Modern browser!  
PostgreSQL 16  
Python 3.12  
fastapi 0.109.0  
pydantic2  

See requirements.txt for full list of python dependencies


## Installation
Create and activate virtual environment  

Install the dependencies
> pip install -r requirements.txt  

Create db in postgres named oppi_dev  

Create the database and populate it with the test data
> python manage.py migrate  
> python manage.py loadinitialdata (populate db with some test data)

The superuser is as follows:
  > email: admin@oppidanspirits.com  
  > password: this15notA$3cur3pa%%w*rd  

## Documentation

The documentation can be viewed at 127.0.0.1:8001 in a browser after running:
>  mkdocs serve -a 127.0.0.1:8001

from a (virtual environment-enabled) shell
