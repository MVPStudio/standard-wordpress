# Standard Wordpress

This is our standard WordPress setup for Kubernetes. People who want to run WordPress on MVPStudio infrastructure can
simply fork this repo and run a few `kubectl` commands to get a running WordPress system.

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
replaced by the actual namespace when the [setup script](#setup-script) is run.

# Setup Script

Details to come.
