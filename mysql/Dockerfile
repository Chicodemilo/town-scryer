# Use official MySQL 8.0 image
FROM mysql:8.0

# Set environment variables for MySQL
ENV MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}
ENV MYSQL_DATABASE=${MYSQL_DATABASE}
ENV MYSQL_USER=${MYSQL_USER}
ENV MYSQL_PASSWORD=${MYSQL_PASSWORD}

# Copy initialization scripts
COPY ./init/ /docker-entrypoint-initdb.d/

# Copy custom MySQL configuration if needed
# COPY ./my.cnf /etc/mysql/conf.d/

# Expose MySQL port
EXPOSE 3306

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD mysqladmin ping -h localhost -u $MYSQL_USER -p$MYSQL_PASSWORD || exit 1

# Use the default MySQL entrypoint
CMD ["mysqld"]