## reNgine

### A simple recon engine

Currently in Alpha stage!

### How to run?

`git clone https://github.com/yogeshojha/rengine`

`cd rengine`

`docker-compose up --build`

Once build is done, run the migration
`docker exec -it rengine_web_1 python manage.py migration`

Then run docker normally
`docker-compose up`
