# CI/CD Secrets (GitHub Actions)

Добавьте в Settings → Secrets and variables → Actions:

- SSH_HOST — публичный IP/домен сервера
- SSH_USER — пользователь для SSH (например, ubuntu)
- SSH_KEY — приватный SSH ключ (BEGIN/END OPENSSH PRIVATE KEY)

(Опционально)
- SSH_PORT — нестандартный порт SSH, если не 22

Убедитесь, что на сервере:
- установлен docker и docker compose
- создан каталог DEPLOY_PATH и в нём лежит боевой .env
- пользователь имеет право запускать docker (добавлен в группу docker)
