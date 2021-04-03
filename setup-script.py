import argparse
import base64
import logging
from pathlib import Path
import secrets
import shutil
import string
import sys
from typing import Dict, List, cast

from kubernetes import kubernetes
from pybars import Compiler


THIS_DIR = Path(__file__).parent
K8_DIR = THIS_DIR / 'k8s'

log = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)-15s %(message)s')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Generate Kubernetes manifest files for a WordPress setup.')
    parser.add_argument('-o', '--out', required=True, type=Path,
                        help='Path to a directory where the generated Kubernetes files should be written')
    parser.add_argument('-d', '--dry_run', action='store_true', default=False,
                        help='If given the manifest files will not be applied to the cluster, they will just '
                        'be generated to --out.')
    parser.add_argument('--no_secrets', action='store_true', default=False,
                        help='Skip the automatic generation of the database and WordPress secrets. You will have to '
                        'manually create the secrets.')
    parser.add_argument('-n', '--namespace', type=str,
                        help='The Kubernetes namespace to which the WordPress site will be deployed.')
    parser.add_argument('-t', '--title', type=str, 
                        help='The title for your WordPress site')
    parser.add_argument('-u', '--hostname', type=str,
                        help='The hostname that will be used for your production WordPress site. This is the base '
                        'URL _excluding_ any http:// or https:// prefix.')
    parser.add_argument('-p', '--project_name', type=str, default=None,
                        help='A "project" name to be used in Kubernetes config files and such as an indentifier. By '
                        'default this will be the hostname with characters like `.` replaced by `-`')

    parsed = parser.parse_args()

    prompt_if_missing = ['namespace', 'title', 'hostname']

    parsed_dict = vars(parsed)
    for opt in prompt_if_missing:
        if opt not in parsed_dict or parsed_dict[opt] is None:
            val = input(opt + ': ')
            setattr(parsed, opt, val)

    if parsed.hostname.startswith('http') or parsed.hostname.find('://') != -1:
        log.error('The --hostname argument must not include the http or https prefix. It should be just the hostname.')
        log.error('For example, if the site is at http://mvpstudio.org then --hostname should be mvpstudio.org.')
        parser.print_help()
        sys.exit(1)

    if parsed.project_name is None:
        pn = parsed.hostname.replace('.', '-')
        log.info('Setting project name to %s', pn)
        setattr(parsed, 'project_name', pn)

    return parsed


def gen_password() -> str:
    """Generates a secure, random password and returns it."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(10))


def gen_and_store_mdb_secrets(k8_client: kubernetes.client.CoreV1Api, namespace: str) -> None:
    """Generate and store the k8's secrets for MariaDb.

    This includes the user and admin passwords.

    Args:
        k8_client: a configured CoreV1Api k8's client.
        namespace: the namespace in which to create the secrets.
    """
    body = kubernetes.client.V1Secret(
        string_data={
            'user-password': gen_password(),
            'root-password': gen_password()})
    body.metadata = {'name': 'mdbsecrets'}
    log.info('Creating database secrets')
    try:
        k8_client.create_namespaced_secret(namespace=namespace, body=body)
    except kubernetes.client.ApiException as e:
        if e.status == 409:
            log.info('Secret was already created. Will not over-write it.')
        else:
            raise e


def gen_and_store_wp_secrets(k8_client: kubernetes.client.CoreV1Api, namespace: str) -> str:
    """Generate and store the WordPress secrets.

    This includes the password for the admin user

    Args:
        k8_client: a configured CoreV1Api k8's client.
        namespace: the namespace in which to create the secrets.

    Returns:
        The password for the admin user. This can be used to log into the new WordPress instance.
    """
    admin_pass = gen_password()
    body = kubernetes.client.V1Secret(string_data={'admin-password': admin_pass})
    body.metadata = {'name': 'wpsecrets'}
    log.info('Creating  WordPress secrets')

    try:
        k8_client.create_namespaced_secret(namespace=namespace, body=body)
    except kubernetes.client.ApiException as e:
        if e.status == 409:
            log.info('Admin password already exists.')
            # Now we have to fetch that password so we can return it to the user
            secret = cast(kubernetes.client.V1Secret,
                          k8_client.read_namespaced_secret(name='wpsecrets', namespace=namespace))
            admin_pass = base64.b64decode(secret.data['admin-password']).decode('utf-8')

    return admin_pass

def generate_manifests(template_vars: Dict[str, str], dest: Path) -> None:
    """Given template_vars, a dict from template variable name to the value for that variable, recursively find all
    files under K8_DIR, expand them as handlebars templates if they have a .tmpl.yaml extension, and copy them to the
    same relative location in dest.  Files found under K8_DIR that do not end with .tmpl.yaml are copied unchanged to
    dest.
    """
    compiler = Compiler()

    TEMPLATE_SUFFIX = '.tmpl.yaml'

    # As we walk cur_dir we'll find additional subdirectories which we'll push here to be explored in later iterations.
    to_explore: List[Path] = [K8_DIR.absolute()]
    while len(to_explore) > 0:
        cur_dir = to_explore.pop().absolute()
        log.info('Looking for Kubernetes files in %s', cur_dir)
        for file_or_dir in cur_dir.iterdir():
            if file_or_dir.is_dir():
                to_explore.append(file_or_dir)
            else:
                dest_file = dest / file_or_dir.relative_to(K8_DIR)
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                if str(file_or_dir).endswith(TEMPLATE_SUFFIX):
                    dest_file = dest_file.parent / (str(dest_file)[:-len(TEMPLATE_SUFFIX)] + '.yml')
                    log.info('Expanding template %s to %s', file_or_dir, dest_file)
                    with open(file_or_dir, 'rt', encoding='utf-8') as inf:
                        contents = inf.read()
                        template = compiler.compile(contents)
                        out_contents = template(template_vars)
                        with open(dest_file, 'wt', encoding='utf-8') as outf:
                            outf.write(out_contents)
                else:
                    log.info('Copying %s to %s', file_or_dir, dest_file)
                    shutil.copy(file_or_dir, dest_file)


def main() -> None:
    args = parse_args()
    if not args.dry_run:
        kubernetes.config.load_kube_config()
        k8_client = kubernetes.client.CoreV1Api()

        if not args.no_secrets:
            gen_and_store_mdb_secrets(k8_client, args.namespace)
            
            wp_admin_pass = gen_and_store_wp_secrets(k8_client, args.namespace)
            print('Admin password for the new WordPress site:', wp_admin_pass)

    template_vars = {
        'namespace': args.namespace,
        'site-title': args.title,
        'hostname': args.hostname,
        'project-name': args.project_name,
    }
    generate_manifests(template_vars, args.out)


if __name__ == '__main__':
    main()
