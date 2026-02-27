# Final Project
## Team Members
Christian
James 
Maria
Emin
Matthew
Hamza


## Rest the environment for these new models
- docker compose down -v
- docker compose up -d --build
- docker compose exec app python app/manage.py makemigrations
- docker compose exec app python app/manage.py migrate

## Create admin access - to access the backend and add data manually, create superuser
- docker compose exec app python app/manage.py createsuperuser
- navigate to http://localhost:8000/admin/