from pybars import Compiler
from pathlib import Path
from typing import Dict, List
import argparse
import io
import logging
import shutil


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
    parser.add_argument('-n', '--namespace', type=str, required=True,
                        help='The Kubernetes namespace to which the WordPress site will be deployed.')

    return parser.parse_args()


def generate_manifests(template_vars: Dict[str, str], dest: Path) -> None:
    """Given template_vars, a dict from template variable name to the value for that variable, recursively find all
    files under K8_DIR, expand them as handlebars templates if they have a .tmpl extension, and copy them to the same
    relative location in dest. Files found under K8_DIR that do not end with .tmpl are copied unchanged to dest.
    """
    compiler = Compiler()

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
                if file_or_dir.suffix == '.tmpl':
                    dest_file = dest_file.parent / (dest_file.stem + '.yml')
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
        'namespace': args.namespace
    }
    generate_manifests(template_vars, args.out)


if __name__ == '__main__':
    main()
