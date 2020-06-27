<h1 align="center">Welcome to reNgine 👋</h1>
<p>
  <a href="https://twitter.com/ojhayogesh11" target="_blank">
    <img alt="Twitter: ojhayogesh11" src="https://img.shields.io/twitter/follow/ojhayogesh11.svg?style=social" />
  </a>
</p>

> A simple recon engine

## Install

```sh
git clone https://github.com/yogeshojha/rengine
cd rengine
docker-compose up --build
```

Once Build is over, stop the docker by pressing ctrl + c and then run migrations

```sh
docker exec -it rengine_web_1 python manage.py migrate
```

Now, run the docker normally

```sh
docker-compose up
```

## Author

👤 **Yogesh Ojha**

* Website: http://yogeshojha.com
* Twitter: [@ojhayogesh11](https://twitter.com/ojhayogesh11)
* Github: [@yogeshojha](https://github.com/yogeshojha)

## Show your support

Give a ⭐️ if this project helped you!

***
