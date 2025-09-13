FROM nginx:1.25-alpine

# Копируем пользовательскую конфигурацию nginx
COPY docker/nginx/nginx.conf /etc/nginx/nginx.conf

# Создаём папки для журналов (необязательно)
RUN mkdir -p /var/log/nginx

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
