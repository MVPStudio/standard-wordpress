from pybars import Compiler
import os

DB_MANIFEST_TEMPLATE = 'templates/mariadb.tmpl'
DB_MANIFEST = 'mariadb.yaml'

compiler = Compiler()

with open(DB_MANIFEST_TEMPLATE, 'r') as manifest:
    source = manifest.read().decode('utf-8')
template = compiler.compile(source)

ns = input("Please enter a namespace:\n")
print("Using namespace: " + ns)

with open(DB_MANIFEST, 'w') as manifest:
    manifest.write(template({'namespace': ns}))
