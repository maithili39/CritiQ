# Runs backup.sh on a schedule via busybox crond (bundled with the postgres:16-alpine
# base image, which already has pg_dump matching the target Postgres version).
FROM postgres:16-alpine

RUN apk add --no-cache tar

WORKDIR /app
COPY scripts/backup.sh scripts/backup.sh
COPY scripts/backup-cron/crontab /etc/crontabs/root
RUN chmod +x scripts/backup.sh

CMD ["crond", "-f", "-l", "2"]
