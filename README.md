![Version](https://img.shields.io/badge/version-alpha-blue.svg?cacheSeconds=2592000)
[![first-timers](https://img.shields.io/badge/first--timers--only-friendly-blue.svg?style=flat-square)](https://www.firsttimersonly.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/yogeshojha/rengine/blob/master/LICENSE)
[![python](https://img.shields.io/badge/python-3.7-blue.svg?logo=python&labelColor=blue)](https://www.python.org/downloads/)
[![platform](https://img.shields.io/badge/platform-osx%2Flinux%2Fwindows-green.svg)](https://github.com/yogeshojha/rengine/)
[![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=yogeshojha_rengine&metric=vulnerabilities)](https://sonarcloud.io/dashboard?id=yogeshojha_rengine)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=yogeshojha_rengine&metric=sqale_rating)](https://sonarcloud.io/dashboard?id=yogeshojha_rengine)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=yogeshojha_rengine&metric=alert_status)](https://sonarcloud.io/dashboard?id=yogeshojha_rengine)
![GitHub issues](https://img.shields.io/github/issues/yogeshojha/rengine)


<!-- PROJECT LOGO -->
<br />
<p align="center">
  <a href="https://github.com/yogeshojha/rengine">
    <img src="static/img/logo.png" alt="Logo" width="80" height="80">
  </a>

  <h3 align="center">reNgine</h3>

  <p align="center">
    A simple recon Engine
    <br />
    <a href="https://github.com/yogeshojha/rengine/blob/master/CONTRIBUTING.md">Contribute</a>
    ·
    <a href="https://github.com/yogeshojha/rengine/issues">Report Bug</a>
    ·
    <a href="https://github.com/yogeshojha/rengine/issues">Request Feature</a>
  </p>
</p>

## ➤ Table of Contents

* [About the Project](#about-reNgine)
  * [Motivation behind reNgine](#motivation-behind-starting-rengine)
  * [Screenshots](#screenshots)
  * [Built With](#built-with)
* [Getting Started](#getting-started)
  * [Prerequisites](#prerequisites)
  * [Installation](#installation)
* [Usage](#usage)
* [Roadmap](#roadmap)
* [Contributing](#contributing)
* [License](#license)
* [Acknowledgements](#acknowledgements)

## ➤ About reNgine

![](https://user-images.githubusercontent.com/17223002/86508683-b8070780-bdff-11ea-8e35-f988943b392a.png)

There are many great recon tools out there, however, I didn't find one that suits my need so I created this reNgine. I wanted a recon engine where I could perform end to end recon and visualize the result quickly.

The results produced by the other tools were great! however, I was frustrated of not having everything in one place.

### ➤ Motivation behind starting reNgine
Let's suppose, I am performing recon on redacted.com, and wanted to quickly glance through results like this, I want all subdomains that had **'admin'** on the **page title**, and if there are many of them, sort them by content-length and show me the screenshot.

Also, suppose I am performing recon for anotherredacted.com, after performing the recon, I wanted all subdomains, that were using php as technology, and quickly visually see the screenshot as well.

Honestly, there were not any tools that could automate this entire pipeline. So I started building reNgine.

### ➤ Screenshots
This is what I built

![](https://user-images.githubusercontent.com/17223002/86508684-b9d0cb00-bdff-11ea-996d-74ef776d2672.png)

![](https://user-images.githubusercontent.com/17223002/86508685-ba696180-bdff-11ea-9def-f45e5b059f0f.png)

Of course, at this point in time, reNgine does not give the best result compared other tools. reNgine has its shortcomings. But, I am continuously adding new features. You may help me on this journey by creating a PR filled with new features and bug fixes. Please have a look at the [Contributing](#contributing) section before doing so.

### ➤ Built With
This section should list any major frameworks that you built your project using. Leave any add-ons/plugins for the acknowledgments section. Here are a few examples.
* [Python](https://www.python.org)
* [django](https://www.djangoproject.com)
* [Bootstrap](https://getbootstrap.com)

## ➤ Getting Started

To get a local copy up and running follow these simple example steps.

```sh
git clone https://github.com/yogeshojha/rengine.git
cd rengine
```

### ➤ Prerequisites

* Docker
Install docker based on your OS from [here](https://www.docker.com/get-started)
* docker-compose
Installation instructions for docker-compose from [here](https://docs.docker.com/compose/install/)

### ➤ Installation

1. Assuming that you have followed the above steps and inside rengine directory
```sh
docker-compose up --build -d
```
Build process may take some time
3. Run the migration
```sh
docker exec -it rengine_web_1 python manage.py migrate
```

## ➤ Usage

If the installation is successful, then you can simply run the engine by running
```sh
docker-compose up -d
```

## ➤ Roadmap

Currently, reNgine performs only basic reconnaissance. Please have a look at [Project todo list](https://github.com/yogeshojha/rengine/projects/1) to see the coming awesome features and tweaks.

## ➤ Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**. Your contributions could be as simple as fixing the indentations or fixing UI to as complex as bringing new modules and features.

See [the contributing guide](CONTRIBUTING.md) to get started.

### ➤ First-time Open Source contributors
Please note that reNgine is beginner-friendly. If you have never done any open-source yet, we encourage you to do so. **We will be happy and proud of your first PR ever.**

You can begin with resolving any [open issues](https://github.com/yogeshojha/rengine/issues).

## ➤ License

Distributed under the GNU GPL license License. See [LICENSE](LICENSE) for more information.

## ➤ Acknowledgements
reNgine is just a pipeline of recon. reNgine would not have been possible without the following individuals/organizations.

* Amass: [OWASP](https://github.com/OWASP/)
* httpx, subfinder, naabu: [ProjectDiscovery](https://github.com/projectdiscovery/)
* Sublist3r: [Ahmed Aboul-Ela](https://github.com/aboul3la/)
* gau, assetfinder: [Tom Hudson](https://github.com/tomnomnom/assetfinder)
* dirsearch [maurosoria](https://github.com/maurosoria/dirsearch)
