#!/bin/sh
certbot certonly --webroot -w /var/www/certbot \
    -d roman-it.dev \
    --email rvkstudent@yandex.ru \
    --noninteractive \
    --agree-tos