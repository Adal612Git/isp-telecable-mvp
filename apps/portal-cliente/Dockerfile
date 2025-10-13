FROM nginx:1.27-alpine
COPY apps/portal-cliente/nginx.conf /etc/nginx/conf.d/default.conf
COPY apps/portal-cliente/public /usr/share/nginx/html
COPY apps/portal-cliente/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
EXPOSE 80
ENTRYPOINT ["/entrypoint.sh"]
