"""Build the independently installed OSGi lifecycle observer package."""
import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def build(bundle: Path, output: Path) -> None:
    root = "/apps/wknd-demo/lifecycle/install"
    with ZipFile(output, "w", ZIP_DEFLATED) as package:
        package.writestr("META-INF/vault/filter.xml",
                         f'<workspaceFilter version="1.0"><filter root="{root}"/></workspaceFilter>')
        package.writestr("META-INF/vault/properties.xml", """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE properties SYSTEM "http://java.sun.com/dtd/properties.dtd">
<properties>
    <entry key="group">wknd-demo</entry>
    <entry key="name">wknd-lifecycle-observer</entry>
    <entry key="version">1.0.0</entry>
    <entry key="packageType">application</entry>
</properties>
""")
        package.write(bundle, f"jcr_root{root}/lifecycle.jar")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.bundle, args.output)
