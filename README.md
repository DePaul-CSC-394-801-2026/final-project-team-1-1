# Final Project
## Team Members
Christian
James 
Maria
Emin
Matthew
Hamza


## Seeding the database, to test out search w.i.p.
- Probably need to delete everything first
- `docker compose down -v`
- Migrate
- `docker compose up -d`
- `docker compose exec app python app/manage.py makemigrations pages`
- `docker compose exec app python app/manage.py migrate`
- Then seed: `docker compose exec app python app/manage.py seed_projects`
