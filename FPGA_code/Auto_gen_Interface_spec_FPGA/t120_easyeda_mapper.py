#!/usr/bin/env python3
"""Extract T120 connections from EasyEDA EPRU and optionally fill Efinix XML.

The EPRU file is a record-per-line format.  PAD_NET records are the source of
truth for component pad to net connections; the workbook supplies the
package-pin to Efinix circuit-pin translation.
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET


TARGET_DESIGNATOR = "U100$CBB22"
TARGET_DEVICE = "T120F324"
XML_NS = "http://www.efinixinc.com/peri_design_db"
ET.register_namespace("efxpt", XML_NS)
SKIP_EXTERNAL_TYPES = {
    "W25Q128JVSIQ",
    "W25Q64JVZPIQ",
    "0402WGF1000TCE",
}
GPIO_DEF_PATTERN = re.compile(
    r"^(GPI(?:OL|OR)_\d+|GPIOT_(?:RXP|RXN|TXP|TXN)\d+|"
    r"GPIOB_(?:TXP|TXN|RXP|RXN)\d+)"
)


def is_skipped_external_type(device_type: str) -> bool:
    return device_type in SKIP_EXTERNAL_TYPES or device_type.startswith("0402")


def sanitize_name(value: str) -> str:
    """Convert an EasyEDA net name to an Efinix-safe identifier."""
    value = value.rsplit("\\", 1)[-1]
    value = value.replace("\\", "_")
    value = re.sub(r"[^A-Za-z0-9_]", "_", value)
    return re.sub(r"_+", "_", value).strip("_") or "UNNAMED"


def parse_epru(path: Path) -> tuple[
    dict[str, str], list[dict[str, str]], dict[str, dict[str, str]], dict[str, str]
]:
    """Return component-id to designator and all PAD_NET connections."""
    designators: dict[str, str] = {}
    pad_nets: list[dict[str, str]] = []
    pin_definitions: dict[str, dict[str, str]] = defaultdict(dict)
    component_devices: dict[str, str] = {}
    device_titles: dict[str, str] = {}
    current_device_id = ""

    with path.open("r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            left, _, right = line.rstrip("\n").partition("||")
            try:
                record = json.loads(left)
            except json.JSONDecodeError:
                continue

            record_type = record.get("type")
            try:
                payload = json.loads(right.rstrip("|") ) if right else None
            except json.JSONDecodeError:
                payload = None

            if record_type == "DOCHEAD" and isinstance(payload, dict):
                current_device_id = payload.get("uuid", "")
            if record_type == "META" and isinstance(payload, dict):
                title = payload.get("title", "")
                if current_device_id and title:
                    device_titles[current_device_id] = title

            if record_type == "ATTR" and isinstance(payload, dict):
                if payload.get("key") == "Designator" and payload.get("parentId"):
                    designators[payload["parentId"]] = payload.get("value", "")
                if payload.get("key") == "Device" and payload.get("parentId"):
                    component_devices[payload["parentId"]] = payload.get("value", "")
                if payload.get("key") in {"Pin Name", "Pin Number"}:
                    part_id = payload.get("partId", "")
                    pin_id = payload.get("parentId", "")
                    if part_id and pin_id:
                        pin_definitions[part_id][f"{pin_id}:{payload['key']}"] = payload.get("value", "")
                continue

            if record_type != "PAD_NET" or not isinstance(record.get("id"), str):
                continue
            try:
                identifier = json.loads(record["id"])
            except json.JSONDecodeError:
                continue
            if not isinstance(identifier, list) or len(identifier) < 3:
                continue
            component_id, pad = identifier[1], identifier[2]
            pad_net = payload.get("padNet", "") if isinstance(payload, dict) else ""
            pad_nets.append(
                {
                    "component_id": component_id,
                    "pad": pad,
                    "raw_net": pad_net,
                    "line": str(line_number),
                }
            )

    return designators, pad_nets, pin_definitions, {
        component_id: device_titles.get(device_id, device_id)
        for component_id, device_id in component_devices.items()
    }


def read_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    return ["".join(node.itertext()) for node in root.findall("x:si", namespace)]


def base_gpio_def(gpio: str) -> str:
    """Return the Efinix GPIO identifier without its functional suffix."""
    match = GPIO_DEF_PATTERN.match(gpio)
    return match.group(1) if match else gpio


def read_t120_pinout(path: Path) -> dict[str, tuple[str, str]]:
    """Read package pin -> (Excel GPIO name, base Efinix GPIO name) from T120_pin_map.xlsx."""
    with zipfile.ZipFile(path) as archive:
        shared = read_shared_strings(archive)
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        rel_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        relationship_root = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relationships = {
            item.attrib["Id"]: item.attrib["Target"]
            for item in relationship_root
        }
        sheet = next(
            item for item in workbook.find("x:sheets", namespace)
            if item.attrib.get("name") == "Sheet1"
        )
        target = relationships[sheet.attrib[f"{{{rel_ns}}}id"]]
        worksheet_path = "xl/" + target.lstrip("/")
        root = ET.fromstring(archive.read(worksheet_path))

        rows: list[list[str]] = []
        for row in root.findall(".//x:sheetData/x:row", namespace):
            values: dict[int, str] = {}
            for cell in row.findall("x:c", namespace):
                ref = cell.attrib.get("r", "A1")
                column = 0
                for char in re.match(r"[A-Z]+", ref).group():
                    column = column * 26 + ord(char) - ord("A") + 1
                value = cell.find("x:v", namespace)
                text = value.text if value is not None and value.text else ""
                if cell.attrib.get("t") == "s" and text:
                    text = shared[int(text)]
                values[column - 1] = text
            if values:
                rows.append([values.get(i, "") for i in range(max(values) + 1)])

    gpio_by_package_pin: dict[str, tuple[str, str]] = {}
    for row in rows[1:]:
        # Column 1 (index 1) contains GPIO names, column 8 (index 8) contains package pins (FBGA324)
        if len(row) > 8:
            gpio = row[1]
            package_pin = row[8]
            if gpio and package_pin and GPIO_DEF_PATTERN.match(gpio):
                base_gpio = base_gpio_def(gpio)
                gpio_by_package_pin[package_pin] = gpio, base_gpio
    return gpio_by_package_pin


def classify_direction(
    net_name: str,
    external_designators: set[str],
    external_pin_names: set[str],
    external_types: set[str],
) -> tuple[str, str]:
    """Classify obvious interface directions and retain confidence metadata."""
    name = net_name.upper()
    if name in {"GND", "3.3V", "3.3VD", "1.2V", "1.2VD"}:
        return "power", "high"
    phy_names = {item.upper() for item in external_pin_names}
    types = {item.upper() for item in external_types}
    if any("PZ2.54" in item or item.startswith("PZ2") for item in types):
        return "input", "high"
    if "74HC595" in types:
        return "output", "high"
    if "XC2361A" in types:
        if any(item.upper() == "SDO" for item in external_pin_names):
            return "input", "high"
        if any(item.upper() in {"SCK", "CONV"} for item in external_pin_names):
            return "output", "high"
    if any("MDIO" in item for item in phy_names):
        return "inout", "high"
    if any("RX" in item or "INTB" in item for item in phy_names):
        return "input", "medium"
    if any("TX" in item or item == "MDC" or "RSTB" in item for item in phy_names):
        return "output", "medium"
    if any(token in name for token in ("RX", "INT", "RSTB", "RESET")):
        return "input", "medium"
    if any(token in name for token in ("TX", "MDC", "CLK", "SCK", "CONV")):
        return "output", "medium"
    if external_designators:
        return "unknown", "low"
    return "unknown", "low"


def build_intermediate(
    source: Path, pinout: Path, designator: str = TARGET_DESIGNATOR
) -> dict:
    designators, pad_nets, pin_definitions, component_devices = parse_epru(source)
    component_ids = {item for item, name in designators.items() if name == designator}
    if not component_ids:
        raise ValueError(f"Could not find designator {designator!r}")

    by_net: dict[str, list[dict[str, str]]] = defaultdict(list)
    for item in pad_nets:
        if item["raw_net"]:
            by_net[item["raw_net"]].append(item)

    gpio_by_package_pin = read_t120_pinout(pinout)
    pins = []
    unresolved = []
    for item in pad_nets:
        if item["component_id"] not in component_ids or not item["raw_net"]:
            continue
        connected = by_net[item["raw_net"]]
        external = {
            designators.get(other["component_id"], other["component_id"])
            for other in connected
            if other["component_id"] not in component_ids
        }
        external_pin_names = set()
        external_connections = []
        for other in connected:
            external_designator = designators.get(other["component_id"], "")
            device_type = component_devices.get(other["component_id"], "")
            if is_skipped_external_type(device_type):
                continue
            if other["component_id"] not in component_ids:
                external_connections.append(
                    {
                        "component": external_designator or other["component_id"],
                        "type": component_devices.get(other["component_id"], "?"),
                        "pin_number": other["pad"],
                        "pin_name": "?",
                    }
                )
            for part_id, definitions in pin_definitions.items():
                if device_type and not part_id.startswith(device_type + "."):
                    continue
                for pin_id, pin_number in definitions.items():
                    if pin_id.endswith(":Pin Number") and pin_number == other["pad"]:
                        name_key = pin_id.replace(":Pin Number", ":Pin Name")
                        if name_key in definitions:
                            pin_name = definitions[name_key]
                            external_pin_names.add(pin_name)
                            for connection in external_connections:
                                if (
                                    connection["component"] == external_designator
                                    and connection["pin_number"] == other["pad"]
                                ):
                                    connection["pin_name"] = pin_name
        net_name = sanitize_name(item["raw_net"])
        external_types = {
            connection["type"]
            for connection in external_connections
            if connection["type"] != "?"
        }
        mode, confidence = classify_direction(
            item["raw_net"], external, external_pin_names, external_types
        )
        source_gpio_def, gpio_def = gpio_by_package_pin.get(item["pad"], ("", ""))
        pin = {
            "name": net_name,
            "raw_net": item["raw_net"],
            "package_pin": item["pad"],
            "source_gpio_def": source_gpio_def,
            "gpio_def": gpio_def,
            "mode": mode,
            "direction_confidence": confidence,
            "external_components": sorted(external),
            "external_pin_names": sorted(external_pin_names),
            "external_connections": external_connections,
            "source_line": int(item["line"]),
        }
        pins.append(pin)
        if not gpio_def or mode == "unknown":
            unresolved.append(pin)

    pins.sort(key=lambda item: (item["package_pin"], item["name"]))
    return {
        "device": TARGET_DEVICE,
        "designator": designator,
        "source": str(source),
        "pinout": str(pinout),
        "pins": pins,
        "unresolved": unresolved,
    }


def append_gpio_elements(xml_path: Path, output_path: Path, mapping: dict) -> None:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    gpio_info = root.find(f"{{{XML_NS}}}gpio_info")
    if gpio_info is None:
        raise ValueError("XML template has no gpio_info element")

    pins_by_name = {pin["name"]: pin for pin in mapping["pins"]}
    existing = {
        item.attrib.get("name"): item
        for item in gpio_info.findall(f"{{{XML_NS}}}gpio")
    }
    for name, gpio in existing.items():
        pin = pins_by_name.get(name)
        if pin and pin["gpio_def"]:
            gpio.set("gpio_def", pin["gpio_def"])

    global_unused = gpio_info.find(f"{{{XML_NS}}}global_unused_config")
    if global_unused is not None:
        gpio_info.remove(global_unused)
    for pin in mapping["pins"]:
        if not pin["gpio_def"] or pin["mode"] not in {"input", "output", "inout"}:
            continue
        if pin["name"] in existing:
            continue
        gpio = ET.SubElement(
            gpio_info,
            f"{{{XML_NS}}}gpio",
            name=pin["name"],
            gpio_def=pin["gpio_def"],
            mode="input" if pin["mode"] == "inout" else pin["mode"],
            bus_name="",
            is_lvds_gpio="false",
            io_standard="3.3 V LVTTL / LVCMOS",
        )
        if pin["mode"] == "output":
            ET.SubElement(
                gpio,
                f"{{{XML_NS}}}output_config",
                name=pin["name"], name_ddio_lo="", register_option="none",
                clock_name="", is_clock_inverted="false", is_slew_rate="false",
                tied_option="none", ddio_type="none", drive_strength="1",
            )
        else:
            ET.SubElement(
                gpio,
                f"{{{XML_NS}}}input_config",
                name=pin["name"], name_ddio_lo="", conn_type="normal",
                is_register="false", clock_name="", is_clock_inverted="false",
                pull_option="none", is_schmitt_trigger="false", ddio_type="none",
            )
    if global_unused is not None:
        gpio_info.append(global_unused)
    ET.indent(tree, space="    ")
    tree.write(output_path, encoding="UTF-8", xml_declaration=True)


def write_review_report(path: Path, mapping: dict) -> None:
    """Write a compact human-readable pin review list."""
    lines = [
        "T120 FPGA I/O REVIEW",
        "====================",
        "",
        "Review mode values and replace them with the direction confirmed from the external circuit:",
        "  input / output / inout / power / unknown",
        "",
        "Columns: package pin | Excel GPIO (before) | Efinix GPIO (after) | net | current mode | confidence | External circuit Type",
        "",
    ]
    for pin in mapping["pins"]:
        if pin["mode"] == "power":
            external = "power/ground net"
        else:
            external_items = [
                f"{item['type']} ({item['component']}) : "
                f"{item['pin_number']} : {item['pin_name']}"
                for item in pin.get("external_connections", [])
            ]
            visible_items = external_items[:8]
            external = ", ".join(visible_items)
            if len(external_items) > len(visible_items):
                external += f", ... (+{len(external_items) - len(visible_items)} more)"
        lines.append(
            f"{pin['package_pin']:>4} | {pin['source_gpio_def'] or '-':<22} | "
            f"{pin['gpio_def'] or '-':<17} | "
            f"{pin['name']:<32} | {pin['mode']:<7} | "
            f"{pin['direction_confidence']:<6} | {external or '-'}"
        )
    lines.extend(["", "UNRESOLVED COUNT: " + str(len(mapping["unresolved"]))])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--pinout", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--xml-template", type=Path)
    parser.add_argument("--xml-output", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    mapping = build_intermediate(args.source, args.pinout)
    args.json.write_text(json.dumps(mapping, indent=2), encoding="utf-8")
    if bool(args.xml_template) != bool(args.xml_output):
        parser.error("--xml-template and --xml-output must be supplied together")
    if args.xml_template:
        append_gpio_elements(args.xml_template, args.xml_output, mapping)
    if args.report:
        write_review_report(args.report, mapping)


if __name__ == "__main__":
    main()