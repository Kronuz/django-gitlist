#!/bin/sh

# This compiles Scss files and copies fonts from the vendor directories

if [ ! -d vendor/bootstrap.sass ] || [ ! -d vendor/font-awesome-sass ]; then
	echo "You need the bootstrap sass and font-awesome sass projects in the vendor directory!"
	exit 1
fi

scss -t compressed -Igitlist/static/scss -Ivendor/bootstrap.sass/assets/stylesheets -Ivendor/font-awesome-sass/assets/stylesheets gitlist/static/scss/style.scss > gitlist/static/css/style.css
scss -t compressed -Igitlist/static/scss -Ivendor/bootstrap.sass/assets/stylesheets -Ivendor/font-awesome-sass/assets/stylesheets gitlist/static/scss/fontawesome.scss > gitlist/static/css/fontawesome.css
cp vendor/bootstrap.sass/assets/javascripts/bootstrap.min.js gitlist/static/js/bootstrap.js

cp -R vendor/font-awesome-sass/assets/fonts/* gitlist/static/fonts
cp -R vendor/bootstrap.sass/assets/fonts/* gitlist/static/fonts
