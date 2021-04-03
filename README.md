# Standard Wordpress

This is our standard WordPress setup for Kubernetes. People who want to run WordPress on MVPStudio infrastructure can
simply fork this repo and run a few `kubectl` commands to get a running WordPress system.

# Quick Start

TODO: Instructions here for how to get up and running as quick as possible.

## Redirects

WordPress _really_ wants to redirect the user to whatever URL was set as `$WP_HOME`. That's often helpful for SEO and
such but it makes it hard for one of the most common patterns: you first set up a site to replace an existing site and
then you make it live. The [official instructions](https://wordpress.org/support/article/moving-wordpress/) to change
the URL of a WordPress site require dumping the entire DB, then running a search-and-replace on it to replace all the
places where the initial URL got saved to the database, and then reloading the DB. Instead, it'd be nice to temporarily
disable URL redirects. To that end our `docker-entrypoint.sh` script adds the following to your `wp-config.php`:

```php
define( 'WP_HOME', "http://" . $_SERVER["SERVER_NAME"] );
define( 'WP_SITEURL', WP_HOME . "/" );
```

This disables the redirects which allows you to edit the site. Before you go live you might want to remove them. To do
so you can find them in `wp-config.php` right before the line that says:

```php
/* That's all, stop editing! Happy publishing. */
```

# Repo Structure

The repo is has 2 main subdirectories:

1. `docker`: holds `Dockerfiles` and such to generate the images we deploy.
2. `k8s`: holds the Kubernetes manifest files to start all the services, pods, etc.

The `k8s` directory has 2 subdirectories under it:

1. `running`: these are the configuration files that represent services, deployments, etc. that should generally be up
   and running for a healthy site. This includes WordPress, the service for WordPress, the database, the persistent
   volumes, etc.
2. `maintenance`: these are configuration files that _can_ launch additional services but these generally aren't
   running. For example, we _can_ start PHPMyAdmin to give GUI access to the DB in case there's an issue. However, this
   is rarely needed and it's a security concern so we don't run this unless it's necessary and then we run it only until
   the issue is resolved.

In addition a `routing.yaml` file is produced. This must be applies in the `ambassador-edge` namespace and this is
managed by the cluster admins (i.e. MVP Studio volunteers) so this file should be sent to an administrator to be
applied.

The k8s manifest files are standard Kubernetes configuration files _except_ there are some details that are specific
to individual deployments like the namespace, hostname for routing, etc. These are therefore specified using [Handlebars
template format](https://handlebarsjs.com/). For example, a service configuration might look like:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: mariadb
  namespace: {{ namespace }}
  labels:
    app: mariadb
spec:
  ports:
    - port: 3306
      name: mariadb
  selector:
    app: mariadb
```

Note that this is a normal configuration file except that the `namespace` is given as `{{ namespace }}`. This will be
replaced by the actual namespace when the [setup script](#setup-script.py) is run.

The available handlebars variables are:
TODO: finish this!

# Setup Script

In order to run the setup script you will need a few packages installed. To likely want to install them into a
[venv](https://docs.python.org/3/tutorial/venv.html) and install the required files there:

```bash
$ python3 -m venv venv
$ source venv/bin/activate
(venv) $ pip install -r requirements.txt
```

Set up your MariaDB password using Kubernetes secrets.

```bash
kubectl create secret generic mdbsecrets \
  --from-literal=password='eightefferrorsgalore'
  --from-literal=user-password='eightefferrorsgalore'
```

Run setup-script.py to generate all the kube manifest files and have them pushed to the cluster.

```
python setup-script.py
```

TODO: Have the script apply the mariadb manifest file.


# Runs from Volume Mount

We could run WordPress right out of the container. That is, the `index.php` and other associated files that make up the
WordPress install would be inside the container. This would be how most other Docker-based things are run. And it'd have
the advantage of easy rollbacks to previous versions, atomic upgrades, etc. However, this has some significant
downsides:

* In order to upgrade you have to build a new Docker image and deploy it.
* Some GUI tools in the standard WordPress UI (e.g. the "upgrade button") assume they can modify files on the disk
  directly.

Since most WordPress users are familiar with the GUI tools and not Docker and Kubernetes we decided to set things up in
a way that would be more familiar. Our main container _copies_ the entire WordPress install to `/var/www/html` if it
finds that directory is empty. If it's not empty it doesn't touch it. This way we can volume mount in a `/var/www/html`
via persistent storage. On first run WordPress will get installed to that volume and it won't be touched after that.
This means that users can click the "upgrade" button, install themes, etc. and these changes will persist even if a new
container is deployed (e.g. with an upgrade to Apache).
