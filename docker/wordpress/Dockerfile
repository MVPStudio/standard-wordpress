from wordpress:5.6.2

COPY php.ini /usr/local/etc/php/php.ini

RUN mv /usr/local/bin/docker-entrypoint.sh /usr/local/bin/wp-setup.sh

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

# Install the WP CLI (https://wp-cli.org/#installing)
RUN curl -o /usr/local/bin/wp-cli.phar https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar && \
   apt-get update && apt-get install -y sudo

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD []
