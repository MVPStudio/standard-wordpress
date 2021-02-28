# MVP Studio Standard WordPress Setup

This is our standard WordPress setup for Kubernetes. People who want to run WordPress on MVPStudio infrastructure can
simply fork this repo and run a few `kubectl` commands to get a running WordPress system.

## Runs from Volume Mount

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
