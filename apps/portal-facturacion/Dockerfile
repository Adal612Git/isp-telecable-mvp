FROM nginx:1.27-alpine
WORKDIR /usr/share/nginx/html
COPY public .
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]
