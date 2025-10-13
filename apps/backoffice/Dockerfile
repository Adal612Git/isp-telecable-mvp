FROM nginx:1.27-alpine
COPY apps/backoffice/nginx.conf /etc/nginx/conf.d/default.conf
COPY apps/backoffice/public /usr/share/nginx/html
COPY apps/backoffice/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
EXPOSE 80
ENTRYPOINT ["/entrypoint.sh"]
