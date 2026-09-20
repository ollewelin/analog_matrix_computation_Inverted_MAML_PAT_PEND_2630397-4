#!/usr/bin/env python3
"""Generate T20F256 Interface Designer GPIO entries from an EasyEDA EPRU."""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET


TARGET_DESIGNATOR = "U1$CBB23"
TARGET_DEVICE = "T20F256"
XML_NS = "http://www.efinixinc.com/peri_design_db"
SERIAL_H_RESISTOR = "0402WGJ0680TCE"
GPIO_DEF_PATTERN = re.compile(
    r"^(GPI(?:OL|OR)_\d+|GPIOT_(?:RXP|RXN|TXP|TXN)\d+|"
    r"GPIOB_(?:TXP|TXN|RXP|RXN)\d+)"
)
H_SIGNAL_PATTERN = re.compile(r"^H_M\d+_[PN][1-8]$")
LED_PATTERN = re.compile(r"^LED(\d+)(?:\$.*)?$")
HEAT_ENABLE_PATTERN = re.compile(r"^HEAT_[1-4]_EN$")
DIFFERENTIAL_NAME_PATTERN = re.compile(r".*_[PN]$")
POWER_NETS = {"GND", "1.2V", "1.8V", "2.5V", "3.3V", "3.3VD"}

ET.register_namespace("efxpt", XML_NS)


def sanitize_name(value: str) -> str:
    value = value.rsplit("\\", 1)[-1]
    value = re.sub(r"[^A-Za-z0-9_]", "_", value)
    return re.sub(r"_+", "_", value).strip("_") or "UNNAMED"


def base_gpio_def(gpio: str) -> str:
    match = GPIO_DEF_PATTERN.match(gpio)
    return match.group(1) if match else gpio


def parse_epru(path: Path) -> tuple[
    dict[str, str], dict[str, str], dict[str, list[dict[str, str]]], dict[str, dict[str, str]]
]:
    """Return component metadata, pad connections, and symbol pin names."""
    designators: dict[str, str] = {}
    devices: dict[str, str] = {}
    device_titles: dict[str, str] = {}
    component_devices: dict[str, str] = {}
    pad_nets: dict[str, list[dict[str, str]]] = defaultdict(list)
    pin_definitions: dict[str, dict[str, str]] = defaultdict(dict)
    current_device_id = ""

    with path.open("r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            left, _, right = line.rstrip("\n").partition("||")
            try:
                record = json.loads(left)
                payload = json.loads(right.rstrip("|")) if right else None
            except json.JSONDecodeError:
                continue
            record_type = record.get("type")
            if record_type == "DOCHEAD" and isinstance(payload, dict):
                current_device_id = payload.get("uuid", "")
            elif record_type == "META" and isinstance(payload, dict):
                title = payload.get("title", "")
                if current_device_id and title:
                    device_titles[current_device_id] = title
            elif record_type == "ATTR" and isinstance(payload, dict):
                parent_id = payload.get("parentId", "")
                key = payload.get("key")
                value = payload.get("value", "")
                if key == "Designator" and parent_id:
                    designators[parent_id] = value
                elif key == "Device" and parent_id:
                    component_devices[parent_id] = value
                elif key in {"Pin Name", "Pin Number"}:
                    part_id = payload.get("partId", "")
                    if part_id and parent_id:
                        pin_definitions[part_id][f"{parent_id}:{key}"] = value
            elif record_type == "PAD_NET" and isinstance(record.get("id"), str):
                try:
                    identifier = json.loads(record["id"])
                except json.JSONDecodeError:
                    continue
                if len(identifier) >= 3:
                    component_id, pad = identifier[1], identifier[2]
                    pad_nets[component_id].append(
                        {
                            "pad": pad,
                            "net": payload.get("padNet", "") if isinstance(payload, dict) else "",
                            "line": str(line_number),
                        }
                    )

    for component_id, device_id in component_devices.items():
        devices[component_id] = device_titles.get(device_id, device_id)
    return designators, devices, pad_nets, pin_definitions


def read_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    return ["".join(item.itertext()) for item in root.findall("x:si", namespace)]


def read_t20_pinout(path: Path) -> dict[str, tuple[str, str]]:
    """Read FBGA256 package pin -> (Excel GPIO name, Efinix GPIO name)."""
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    relationship_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    with zipfile.ZipFile(path) as archive:
        shared = read_shared_strings(archive)
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = {
            item.attrib["Id"]: item.attrib["Target"]
            for item in ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        }
        sheet = next(item for item in workbook.find("x:sheets", namespace)
                     if item.attrib.get("name") == "Sheet1")
        target = relationships[sheet.attrib[f"{{{relationship_ns}}}id"]]
        root = ET.fromstring(archive.read("xl/" + target.lstrip("/")))

    pinout: dict[str, tuple[str, str]] = {}
    for row in root.findall(".//x:sheetData/x:row", namespace):
        values: dict[int, str] = {}
        for cell in row.findall("x:c", namespace):
            letters = re.match(r"[A-Z]+", cell.attrib.get("r", "A1")).group()
            column = 0
            for letter in letters:
                column = column * 26 + ord(letter) - ord("A") + 1
            value = cell.find("x:v", namespace)
            text = value.text if value is not None and value.text else ""
            if cell.attrib.get("t") == "s" and text:
                text = shared[int(text)]
            values[column - 1] = text
        gpio = values.get(1, "")
        package_pin = values.get(6, "")
        if gpio and package_pin and GPIO_DEF_PATTERN.match(gpio):
            pinout[package_pin] = gpio, base_gpio_def(gpio)
    return pinout


def pin_name_for_pad(
    device: str, pad: str, pin_definitions: dict[str, dict[str, str]]
) -> str:
    for part_id, definitions in pin_definitions.items():
        if device and not part_id.startswith(device + "."):
            continue
        for key, number in definitions.items():
            if key.endswith(":Pin Number") and number == pad:
                return definitions.get(key.replace(":Pin Number", ":Pin Name"), "")
    return ""


def classify_direction(net_name: str, device_names: set[str]) -> str:
    name = net_name.upper()
    devices = {item.upper() for item in device_names}
    if HEAT_ENABLE_PATTERN.match(name):
        return "output"
    if "LED" in name or any("LED" in item for item in devices):
        return "output"
    if H_SIGNAL_PATTERN.match(net_name):
        return "output"
    if any(token in name for token in ("RX", "IN", "SDO")):
        return "input"
    if any(token in name for token in ("TX", "CLK", "LED", "H_M")):
        return "output"
    return "unknown"


def single_ended_name(name: str) -> str:
    """Avoid Interface Designer interpreting a terminal _P/_N as differential."""
    if not H_SIGNAL_PATTERN.match(name) and DIFFERENTIAL_NAME_PATTERN.fullmatch(name):
        return f"{name}1"
    return name


def resistor_partner_net(
    component_id: str, current_net: str, pad_nets: dict[str, list[dict[str, str]]]
) -> str:
    partners = {item["net"] for item in pad_nets[component_id] if item["net"] != current_net}
    return next(iter(partners), "")


def resolved_name(
    raw_net: str,
    connected: list[str],
    designators: dict[str, str],
    devices: dict[str, str],
    pad_nets: dict[str, list[dict[str, str]]],
    components_by_net: dict[str, list[str]],
) -> tuple[str, str, str]:
    """Return interface name, trace resistor, and far-side net for special paths."""
    if HEAT_ENABLE_PATTERN.match(raw_net):
        return raw_net, "", ""

    if H_SIGNAL_PATTERN.match(raw_net):
        for component_id in connected:
            if devices.get(component_id) == SERIAL_H_RESISTOR:
                return raw_net, designators.get(component_id, component_id), resistor_partner_net(
                    component_id, raw_net, pad_nets
                )

    for component_id in connected:
        if not devices.get(component_id, "").startswith("0402"):
            continue
        far_net = resistor_partner_net(component_id, raw_net, pad_nets)
        if far_net.upper() in POWER_NETS:
            continue
        leds = [
            LED_PATTERN.match(designators.get(far_component, ""))
            for far_component in components_by_net.get(far_net, [])
        ]
        leds = [led for led in leds if led]
        if len(leds) == 1:
            return f"T20_LED{leds[0].group(1)}", designators.get(component_id, component_id), far_net
    return sanitize_name(raw_net), "", ""


def build_intermediate(source: Path, pinout: Path, designator: str) -> dict:
    designators, devices, pad_nets, pin_definitions = parse_epru(source)
    target_ids = {item for item, value in designators.items() if value == designator}
    if not target_ids:
        raise ValueError(f"Could not find T20 designator {designator!r}")
    gpio_by_package_pin = read_t20_pinout(pinout)
    components_by_net: dict[str, list[str]] = defaultdict(list)
    for component_id, pads in pad_nets.items():
        for pad in pads:
            if pad["net"]:
                components_by_net[pad["net"]].append(component_id)

    pins = []
    for target_id in target_ids:
        for item in pad_nets[target_id]:
            raw_net = item["net"]
            connected = components_by_net.get(raw_net, [])
            name, serial_resistor, far_net = resolved_name(
                raw_net, connected, designators, devices, pad_nets, components_by_net
            )
            name = single_ended_name(name)
            source_gpio_def, gpio_def = gpio_by_package_pin.get(item["pad"], ("", ""))
            external_devices = {
                devices.get(component_id, "?")
                for component_id in connected if component_id not in target_ids
            }
            pins.append(
                {
                    "name": name,
                    "raw_net": raw_net,
                    "package_pin": item["pad"],
                    "symbol_pin_name": pin_name_for_pad(
                        devices.get(target_id, ""), item["pad"], pin_definitions
                    ),
                    "source_gpio_def": source_gpio_def,
                    "gpio_def": gpio_def,
                    "mode": classify_direction(name, external_devices),
                    "serial_resistor": serial_resistor,
                    "serial_partner_net": far_net,
                    "source_line": int(item["line"]),
                }
            )
    pins.sort(key=lambda item: (item["package_pin"], item["name"]))
    return {"device": TARGET_DEVICE, "designator": designator, "source": str(source),
            "pinout": str(pinout), "pins": pins}


def add_gpio_config(gpio: ET.Element, name: str, mode: str) -> None:
    config = "output_config" if mode == "output" else "input_config"
    attributes = {"name": name, "name_ddio_lo": "", "ddio_type": "none"}
    if config == "output_config":
        attributes.update(register_option="none", clock_name="", is_clock_inverted="false",
                          is_slew_rate="false", tied_option="none", drive_strength="1")
    else:
        attributes.update(conn_type="normal", is_register="false", clock_name="",
                          is_clock_inverted="false", pull_option="none", is_schmitt_trigger="false")
    ET.SubElement(gpio, f"{{{XML_NS}}}{config}", **attributes)


def append_gpio_elements(template: Path, output: Path, mapping: dict) -> None:
    tree = ET.parse(template)
    gpio_info = tree.getroot().find(f"{{{XML_NS}}}gpio_info")
    if gpio_info is None:
        raise ValueError("XML template has no gpio_info element")
    existing = {item.attrib.get("name"): item for item in gpio_info.findall(f"{{{XML_NS}}}gpio")}
    existing_by_gpio_def = {
        item.attrib.get("gpio_def"): item
        for item in gpio_info.findall(f"{{{XML_NS}}}gpio")
    }
    unused = gpio_info.find(f"{{{XML_NS}}}global_unused_config")
    if unused is not None:
        gpio_info.remove(unused)
    for pin in mapping["pins"]:
        if not pin["gpio_def"] or pin["mode"] not in {"input", "output", "inout"}:
            continue
        gpio = existing.get(pin["name"]) or existing_by_gpio_def.get(pin["gpio_def"])
        if gpio is not None:
            gpio.set("name", pin["name"])
            gpio.set("gpio_def", pin["gpio_def"])
            gpio.set("mode", pin["mode"])
            gpio.set("is_lvds_gpio", str(pin["gpio_def"].startswith("GPIOB_")).lower())
            gpio.set("io_standard", "3.3 V LVTTL / LVCMOS")
            for child in list(gpio):
                if child.tag in {f"{{{XML_NS}}}input_config", f"{{{XML_NS}}}output_config"}:
                    gpio.remove(child)
            add_gpio_config(gpio, pin["name"], pin["mode"])
            continue
        gpio = ET.SubElement(gpio_info, f"{{{XML_NS}}}gpio", name=pin["name"],
                             gpio_def=pin["gpio_def"], mode=pin["mode"], bus_name="",
                             is_lvds_gpio=str(pin["gpio_def"].startswith("GPIOB_")).lower(),
                             io_standard="3.3 V LVTTL / LVCMOS")
        add_gpio_config(gpio, pin["name"], pin["mode"])
    if unused is not None:
        gpio_info.append(unused)
    ET.indent(tree, space="    ")
    tree.write(output, encoding="UTF-8", xml_declaration=True)


def write_connection_report(path: Path, mapping: dict) -> None:
    lines = [
        "T20F256 FPGA CONNECTION REPORT",
        "===============================",
        "",
        "Columns: package pin | Excel GPIO (before) | Efinix GPIO (after) | net | mode | serial resistor | serial partner net",
        "",
    ]
    for pin in mapping["pins"]:
        lines.append(
            f"{pin['package_pin']:>4} | {pin['source_gpio_def'] or '-':<22} | "
            f"{pin['gpio_def'] or '-':<17} | {pin['name']:<24} | "
            f"{pin['mode']:<7} | {pin['serial_resistor'] or '-':<14} | "
            f"{pin['serial_partner_net'] or '-'}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--pinout", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--xml-template", type=Path)
    parser.add_argument("--xml-output", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--designator", default=TARGET_DESIGNATOR)
    args = parser.parse_args()
    mapping = build_intermediate(args.source, args.pinout, args.designator)
    args.json.write_text(json.dumps(mapping, indent=2) + "\n", encoding="utf-8")
    if bool(args.xml_template) != bool(args.xml_output):
        parser.error("--xml-template and --xml-output must be supplied together")
    if args.xml_template:
        append_gpio_elements(args.xml_template, args.xml_output, mapping)
    if args.report:
        write_connection_report(args.report, mapping)


if __name__ == "__main__":
    main()