import argparse
import logging
from pathlib import Path
import secrets
import shutil
import string
from typing import Dict, List, Any

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
    parser.add_argument('-n', '--namespace', type=str,
                        help='The Kubernetes namespace to which the WordPress site will be deployed.')
    parser.add_argument('-t', '--title', type=str, 
                        help='The title for your WordPress site')
    parser.add_argument('-u', '--url', type=str,
                        help='The URL that will be used for your production WordPress site, including the '
                        'protocol (e.g. "https://my.site.com").')


    parsed = parser.parse_args()

    prompt_if_missing = ['namespace', 'title', 'url']

    parsed_dict = vars(parsed)
    for opt in prompt_if_missing:
        if opt not in parsed_dict or parsed_dict[opt] is None:
            val = input(opt + ': ')
            setattr(parsed, opt, val)

    return parsed


def gen_password() -> str:
    """Generates a secure, random password and returns it."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(8))


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
    template_vars = {
        'namespace': args.namespace,
        'site-title': args.title,
        'site-url': args.url
    }
    generate_manifests(template_vars, args.out)


if __name__ == '__main__':
    main()
