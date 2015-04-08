# GitList: an elegant git repository viewer

GitList is an elegant and modern web interface for interacting with multiple git repositories. It allows you to browse repositories using your favorite browser, viewing files under different revisions, commit history, diffs. It also generates RSS feeds for each repository, allowing you to stay up-to-date with the latest changes anytime, anywhere. GitList was initially written in PHP, and ported to Django. GitList is easy to install and easy to customize. Also, the GitList gorgeous interface was made possible due to [Bootstrap](http://twitter.github.com/bootstrap/). 

## Features
* Multiple repository support
* Multiple branch support
* Multiple tag support
* Commit history, blame, diff
* RSS feeds
* Syntax highlighting
* Repository statistics

## Screenshots
[![GitList Screenshot](http://dl.dropbox.com/u/62064441/th1.jpg)](http://cloud.github.com/downloads/klaussilveira/gitlist/1.jpg)
[![GitList Screenshot](http://dl.dropbox.com/u/62064441/th2.jpg)](http://cloud.github.com/downloads/klaussilveira/gitlist/2.jpg)
[![GitList Screenshot](http://dl.dropbox.com/u/62064441/th3.jpg)](http://cloud.github.com/downloads/klaussilveira/gitlist/3.jpg)
[![GitList Screenshot](http://dl.dropbox.com/u/62064441/th4.jpg)](http://cloud.github.com/downloads/klaussilveira/gitlist/4.jpg)
[![GitList Screenshot](http://dl.dropbox.com/u/62064441/th5.jpg)](http://cloud.github.com/downloads/klaussilveira/gitlist/5.jpg)

You can also see a live demo [here](http://gitlist-khornberg.rhcloud.com/).

## Requirements
In order to run GitList on your server, you'll need:

* git
* django 1.6+
* GitPython

## Installation
* Download GitList from [gitlist.org](https://github.com/Kronuz/django_gitlist) and decompress to your `/var/www/gitlist` folder, or anywhere else you want to place GitList.
* Do not download a branch or tag from GitHub, unless you want to use the development version. The version available for download at the website already has all dependencies bundled, so you don't have to use composer or any other tool
* Setup `GITLIST_REPOSITORIES` in `django_gitlist/settings.py`.
* Run `python manage.py runserver`


## Authors and contributors
* [German M. Bravo](https://github.com/Kronuz) (Creator, developer)
* [Klaus Silveira](http://www.klaussilveira.com) (PHP Creator)

## License
[New BSD license](http://www.opensource.org/licenses/bsd-license.php)

## Todo
* improve the current test code coverage
* test the interface
* submodule support
* multilanguage support

## Development

```
git clone https://github.com/Kronuz/django_gitlist.git
```

## Contributing
If you are a developer, we need your help. GitList is a young project and we have lots of stuff to do. Some developers are contributing with new features, others with bug fixes. But you can also dedicate yourself to refactoring the current codebase and improving what we already have. This is very important, we want GitList to be a state-of-the-art application, and we need your help for that.
