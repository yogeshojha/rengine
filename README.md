# Welcome to reNgine 👋
![Version](https://img.shields.io/badge/version-alpha-blue.svg?cacheSeconds=2592000)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/yogeshojha/rengine/blob/master/LICENSE)
[![python](https://img.shields.io/badge/python-3.7-blue.svg?logo=python&labelColor=blue)](https://www.python.org/downloads/)
[![platform](https://img.shields.io/badge/platform-osx%2Flinux%2Fwindows-green.svg)](https://github.com/yogeshojha/rengine/)
[![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=yogeshojha_rengine&metric=vulnerabilities)](https://sonarcloud.io/dashboard?id=yogeshojha_rengine)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=yogeshojha_rengine&metric=sqale_rating)](https://sonarcloud.io/dashboard?id=yogeshojha_rengine)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=yogeshojha_rengine&metric=alert_status)](https://sonarcloud.io/dashboard?id=yogeshojha_rengine)
![GitHub issues](https://img.shields.io/github/issues/yogeshojha/rengine)

> A simple recon engine for pentest
> Please note, this project is in alpha stage. Some of the modules may not work.

## Install

```sh
git clone https://github.com/yogeshojha/rengine
cd rengine
docker-compose up --build
```

## Make Migrations
Once installation is done, Migrations is compulsory

```sh
docker exec -it rengine_web_1 python manage.py migrate
```
## Usage

```sh
docker-compose up
```

## Author

👤 **Yogesh Ojha**

* Website: https://yogeshojha.com
* Twitter: [@ojhayogesh11](https://twitter.com/ojhayogesh11)
* Github: [@yogeshojha](https://github.com/yogeshojha)
* LinkedIn: [@yogeshojha](https://linkedin.com/in/yogeshojha)

## 🤝 Contributing

Contributions, issues and feature requests are welcome!

Feel free to check [issues page](https://github.com/yogeshojha/rengine/issues).

## Thanks

reNgine is just a pipeline of recon. reNgine would not have been possible without the following people/organization.

* Amass: [OWASP](https://github.com/OWASP/)
* httpx, subfinder, naabu: [ProjectDiscovery](https://github.com/projectdiscovery/)
* Sublist3r: [Ahmed Aboul-Ela](https://github.com/aboul3la/)
* gau, assetfinder: [Tom Hudson](https://github.com/tomnomnom/assetfinder)


## Show your support

Give a ⭐️ if this project helped you!


## 📝 License

Copyright © 2020 [Yogesh Ojha](https://github.com/yogeshojha).

This project is [MIT](https://github.com/yogeshojha/rengine/blob/master/LICENSE) licensed.

***
