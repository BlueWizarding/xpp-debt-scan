"""In-memory parser for a PackagesLocalDirectory (PLD) AOT tree.

Layout (verified against live D365 F&O metadata trees):

- ``<PLD>/<Package>/<Model>/Ax<Type>/<Element>.xml`` plus
  ``<PLD>/<Package>/Descriptor/<Model>.xml``.
- Every element is XML with X++ embedded in CDATA: a
  ``SourceCode/Declaration`` block and per-method ``Method/Name`` +
  ``Method/Source`` pairs (tables and forms nest them deeper; we collect
  every ``<Method>`` that carries both children).
- Skipped: ``XppMetadata`` (a duplicate mirror), ``bin`` (compiler stubs),
  ``Resources``, ``Reports`` payloads, ``WebContent``.

Standard library only. Pure functions; a malformed file is skipped, never
fatal.
"""

import os
import re
import xml.etree.ElementTree as ET
from typing import Dict, Iterator, List, Optional

# Model-level subdirectories that are never source models.
SKIP_DIRS = {"XppMetadata", "bin", "Resources", "Reports", "WebContent",
             "Descriptor"}

# The AOT element directories the scanner walks.
ELEMENT_DIRS = {
    "AxClass": "class",
    "AxTable": "table",
    "AxForm": "form",
    "AxDataEntityView": "data_entity",
    "AxCompositeDataEntityView": "composite_entity",
    "AxEnum": "enum",
    "AxEdt": "edt",
    "AxQuery": "query",
    "AxQuerySimple": "query",
    "AxView": "view",
    "AxReport": "report",
    "AxTableExtension": "table_extension",
    "AxFormExtension": "form_extension",
    "AxSecurityRole": "security_role",
    "AxMap": "map",
    "AxMenuItemDisplay": "menu_item_display",
    "AxMenuItemAction": "menu_item_action",
    "AxMenuItemOutput": "menu_item_output",
}

_EXTENDS_RE = re.compile(r"\bextends\s+([A-Za-z_]\w*)")


def _strip_namespaces(root) -> None:
    """Rewrite tags to their local names in place. Some AOT files declare a
    default namespace (``xmlns="Microsoft.Dynamics.AX.Metadata.V6"`` on
    forms, menu items, reports) and some do not; both are treated
    identically."""
    for el in root.iter():
        if isinstance(el.tag, str) and "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]


def _child_text(elem, tag: str) -> Optional[str]:
    child = elem.find(tag)
    return child.text if child is not None else None


def parse_element_file(path: str, element_type: str,
                       package: str, model: str) -> Optional[Dict]:
    """One AOT XML file -> an element dict, or None when unparseable."""
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return None
    _strip_namespaces(root)
    name = _child_text(root, "Name")
    if not name:
        return None

    declaration = None
    src = root.find("SourceCode")
    if src is not None:
        declaration = _child_text(src, "Declaration")

    methods: List[Dict] = []
    for m in root.iter("Method"):
        m_name = _child_text(m, "Name")
        m_src = _child_text(m, "Source")
        if m_name and m_src:
            methods.append({"name": m_name, "source": m_src})

    extends = None
    if declaration:
        m = _EXTENDS_RE.search(declaration)
        if m:
            extends = m.group(1)

    return {
        "name": name,
        "type": element_type,
        "package": package,
        "model": model,
        "path": path,
        "extends": extends,
        "declaration": declaration,
        "methods": methods,
    }


def iter_element_files(pld_root: str) -> Iterator[Dict]:
    """Yield {path, element_type, package, model} for every scannable AOT
    XML file under the PLD, applying the skip rules."""
    for package in sorted(os.listdir(pld_root)):
        pkg_dir = os.path.join(pld_root, package)
        if not os.path.isdir(pkg_dir):
            continue
        for model in sorted(os.listdir(pkg_dir)):
            if model in SKIP_DIRS:
                continue
            model_dir = os.path.join(pkg_dir, model)
            if not os.path.isdir(model_dir):
                continue
            for ax_dir, element_type in ELEMENT_DIRS.items():
                type_dir = os.path.join(model_dir, ax_dir)
                if not os.path.isdir(type_dir):
                    continue
                try:
                    entries = sorted(os.listdir(type_dir))
                except OSError:
                    continue
                for fn in entries:
                    if fn.lower().endswith(".xml"):
                        yield {"path": os.path.join(type_dir, fn),
                               "element_type": element_type,
                               "package": package, "model": model}


def iter_elements(pld_root: str) -> Iterator[Dict]:
    """Yield parsed element dicts for the whole tree."""
    for meta in iter_element_files(pld_root):
        parsed = parse_element_file(meta["path"], meta["element_type"],
                                    meta["package"], meta["model"])
        if parsed:
            yield parsed
