# Docker Image

This is the Docker image for the main WordPress container.

This image will _copy_ the WordPress install from the docker container to `/var/www/html` when it starts if that
directory is empty. See [the main README.md](../../README.md) for details.

TODO: Document how we pre-setup WordPress

## Details

The entrypoint script that ships with WordPress is pretty long and complex and changes from version to version so we
didn't want to make our own. However, we did want to change how things started a little bit so we'd have a chance to
install some plugins and things.

Before we can describe how we modified the standard entrypoint we need to explain how the standard one works. The
standard image copies WordPress to `/var/www/html` as described in [the main README.md](../../README.md). It assumes
`pwd` is `/var/www/html` when it is run. It takes a single command line argument which helps it know how to provision
itself (e.g. if the argument is starts with `apache` it assumes it's not the fpm or cli versions of WordPress so it does
some setup accordingly. The very last line of the script then executes the command line argument directly. For a normal
setup the command line argument is `apache2-foreground` which runs the Apache web server in the foreground thus starting
the main app.

Our Dockerfile moves this entrypoint to `wp-setup.sh` and removes the final line (the one that would execute the command
line argument and start apache). This let's us call the WordPress entrypoint script exactly as written (making upgrades
easier) but then gives us a chance to do other things like install plugins before starting the web server. We then have
our own `docker-entrypoint.sh` script which call `wp-setup.sh` and that is what is set as the container `ENTRYPOINT`.
