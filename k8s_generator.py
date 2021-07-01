import ast
import json
from argparse import ArgumentParser
from collections import deque
from pathlib import Path
from shutil import rmtree
from textwrap import dedent
from typing import Any, Dict

import black
import isort
import requests
from datamodel_code_generator import generate
from datamodel_code_generator.types import StrictTypes


def fetch_k8s_swagger(version: str) -> Dict[str, Any]:
    url = f"https://raw.githubusercontent.com/kubernetes/kubernetes/release-{version}/api/openapi-spec/swagger.json"
    return requests.get(url).json()


def datamodel_code_generator(src: Path, dest: Path) -> None:
    assert src is not None
    assert dest is not None
    generate(
        src,
        output=dest,
        strict_types=(t for t in StrictTypes),
        disable_timestamp=True,
    )


def remap_modules(swagger: Dict[str, Any], root_module: str) -> None:
    remaining = deque([swagger])
    while remaining:
        current = remaining.pop()
        for k in list(current.keys()):
            if isinstance(current[k], dict):
                remaining.append(current[k])
            if isinstance(current[k], str):
                if "io.k8s." in current[k]:
                    current[k] = current[k].replace("io.k8s", root_module)
            if "io.k8s." in k:
                current[k.replace("io.k8s", root_module)] = current[k]
                del current[k]


def _find_class(module: ast.Module, module_name: str, class_name: str) -> ast.ClassDef:
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    raise KeyError(f"Couldn't find class {class_name} in module {module_name}")


def _get_dict_override(klass: ast.ClassDef) -> ast.FunctionDef:
    methods = {
        node.name: node for node in klass.body if isinstance(node, ast.FunctionDef)
    }
    if "dict" in methods:
        return methods["dict"]
    else:
        dict_method: ast.FunctionDef = ast.parse(  # type: ignore
            dedent(
                f"""
                def dict(self: "{klass.name}") -> Dict[str, Any]:
                    return super().dict()
                """
            )
        ).body[0]
        klass.body.append(dict_method)
        return dict_method


def _find_attr(klass: ast.ClassDef, attr_name: str) -> ast.AnnAssign:
    for node in klass.body:
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id") == attr_name:
            return node
    raise KeyError(f"Couldn't find attribute {attr_name} in class {klass.name}.")


def _ensure_import(module: ast.Module, from_name: str, import_name: str) -> None:
    last_import = -1
    for idx, node in enumerate(module.body):
        if isinstance(node, ast.ImportFrom):
            last_import = idx
            if node.module == from_name:
                if import_name not in [n.name for n in node.names]:
                    node.names.append(ast.alias(import_name))
                return
    module.body.insert(
        last_import, ast.parse("from collections import Counter").body[0]
    )


def handle_proplist(swagger: Dict[str, Any], root: Path) -> None:
    for fqdn, spec in swagger["definitions"].items():
        if "properties" not in spec:
            continue
        for attr_name, attrspec in spec["properties"].items():
            if all(
                [
                    attrspec.get("type") == "array",
                    "x-kubernetes-patch-merge-key" in attrspec,
                    attrspec.get("x-kubernetes-patch-strategy") == "merge",
                ]
            ):
                module_name, class_name = fqdn.rsplit(".", 1)
                module_path = root / (
                    module_name.replace(".", "/").replace("-", "_") + ".py"
                )
                with open(module_path) as fd:
                    module = ast.parse(fd.read())
                klass = _find_class(module, module_name, class_name)
                attr = _find_attr(klass, attr_name)
                key_name = attrspec["x-kubernetes-patch-merge-key"]
                if attr.annotation.value.id == "List":  # type: ignore
                    item_required = True
                    item_type = ast.unparse(attr.annotation.slice)  # type: ignore
                else:
                    item_required = False
                    item_type = ast.unparse(attr.annotation.slice.slice)  # type: ignore

                # Override the .dict() method to enforce that proplist only contains unique element keys.
                _ensure_import(module, "collections", "Counter")
                _ensure_import(module, "typing", "Dict")
                _ensure_import(module, "typing", "Any")
                dict_override = _get_dict_override(klass)
                dict_override.body[-1:-1] = ast.parse(
                    dedent(
                        f"""
                            dup_{attr_name} = [
                                k
                                for k, v
                                in Counter([e.{key_name} for e in self.{attr_name} or []]).most_common()
                                if v > 1
                            ]
                            assert not dup_{attr_name}, f"{{self}}.{attr_name} contains duplicated objects: {{dup_{attr_name}}}"
                            """
                    )
                ).body
                if item_required:
                    # Since it is not Optional[List] we assume we need a value.
                    dict_override.body[-1:-1] = ast.parse(
                        dedent(
                            f"""
                            assert (
                                self.{attr_name} != []
                            ), f"{{self}}.{attr_name} is empty which is probably a mistake. Set it to None if that is intended."
                            """
                        )
                    ).body

                # Provide convenience method for getting items in the proplist
                # TODOL Add proper type annotations.
                klass.body.extend(
                    ast.parse(
                        dedent(
                            f"""
                            def get_{attr_name}_by_{key_name}(self: "{class_name}", {key_name}: Any) -> {item_type}:
                                for elmt in self.{attr_name} or []:
                                    if elmt.{key_name} == {key_name}:
                                        return elmt
                                raise KeyError(f"Not element with {key_name}={{{key_name}}}")

                            def has_{attr_name}_with_{key_name}(self: "{class_name}", {key_name}: Any) -> bool:
                                for elmt in self.{attr_name} or []:
                                    if elmt.{key_name} == {key_name}:
                                        return True
                                return False
                            """
                        )
                    ).body
                )

                with open(module_path, "w") as fd:
                    fd.write(ast.unparse(module))


def format_code(root: Path) -> None:
    queue = deque(root.iterdir())
    while queue:
        node = queue.pop()
        if node.is_dir():
            queue.extend(node.iterdir())
        elif node.name.endswith(".py"):
            isort.file(node.absolute())
            with node.open("r") as fd:
                code = fd.read()
            with node.open("w") as fd:
                fd.write(black.format_str(code, mode=black.FileMode()))


def make_imports_absolute(root: Path, dest: Path) -> None:
    current = dest
    while current != root:
        (current / "__init__.py").touch()
        current = current.parent
    queue = deque(dest.iterdir())
    while queue:
        node = queue.pop()
        if node.is_dir():
            queue.extend(node.iterdir())
        elif node.name.endswith(".py"):
            pkg_parts = node.absolute().relative_to(root).parts
            with node.open("r") as fd:
                code = ast.parse(fd.read())
            for astNode in code.body:
                if isinstance(astNode, ast.ImportFrom):
                    if astNode.level > 0:
                        module_prefix = ".".join(pkg_parts[: -astNode.level])
                        astNode.level = 0
                        if astNode.module:
                            astNode.module = module_prefix + "." + astNode.module
                        else:
                            astNode.module = module_prefix
            with node.open("w") as fd:
                fd.write(ast.unparse(code))


def main() -> None:
    parser = ArgumentParser(
        "Generate all the code to define configs for a give k8s version."
    )
    parser.add_argument("version", help="Version of the k8s API to generate code for.")
    args = parser.parse_args()
    version = args.version
    version_module = "v" + version.replace(".", "_")
    root = Path("__file__").parent.absolute()
    swagger = fetch_k8s_swagger(version)
    swagger_path = root / f"{version_module}.json"
    remap_modules(swagger, f"k8sgencfg.{version_module}")
    with swagger_path.open("w") as fd:
        json.dump(swagger, fd, sort_keys=True, indent=2)
    dest = root / "k8sgencfg" / version_module
    dest.mkdir(parents=True, exist_ok=True)
    rmtree(dest)
    datamodel_code_generator(swagger_path, root)
    handle_proplist(swagger, root)
    make_imports_absolute(root, dest)
    format_code(dest)


if __name__ == "__main__":
    main()
