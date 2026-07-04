import re
import json

CONFIG_PATH = "data/configs/sample_router1.cfg"

def load_config(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def parse_hostname(text):
    match = re.search(r"^hostname\s+(\S+)", text, re.MULTILINE)
    return match.group(1) if match else None

def parse_interfaces(text):
    interfaces = []
    # Find each "interface ..." block up to the next "interface", "!", or end of text
    blocks = re.findall(r"(interface\s+\S+.*?)(?=\ninterface\s|\n!|\Z)", text, re.DOTALL)
    for block in blocks:
        if block.strip().startswith("interface"):
            name_match = re.search(r"interface\s+(\S+)", block)
            desc_match = re.search(r"description\s+(.+)", block)
            ip_match = re.search(r"ip address\s+(\S+)\s+(\S+)", block)
            status = "up" if "no shutdown" in block else "down/unspecified"

            interfaces.append({
                "name": name_match.group(1) if name_match else None,
                "description": desc_match.group(1).strip() if desc_match else None,
                "ip_address": ip_match.group(1) if ip_match else None,
                "subnet_mask": ip_match.group(2) if ip_match else None,
                "status": status
            })
    return interfaces

def parse_ospf(text):
    ospf_match = re.search(r"router ospf\s+(\d+)(.*?)(?=\n!|\Z)", text, re.DOTALL)
    if not ospf_match:
        return None

    process_id = ospf_match.group(1)
    ospf_block = ospf_match.group(2)

    router_id_match = re.search(r"router-id\s+(\S+)", ospf_block)
    networks = re.findall(r"network\s+(\S+)\s+(\S+)\s+area\s+(\S+)", ospf_block)
    passive_interfaces = re.findall(r"passive-interface\s+(\S+)", ospf_block)

    return {
        "process_id": process_id,
        "router_id": router_id_match.group(1) if router_id_match else None,
        "networks": [
            {"network": n[0], "wildcard": n[1], "area": n[2]} for n in networks
        ],
        "passive_interfaces": passive_interfaces
    }

def parse_bgp(text):
    bgp_match = re.search(r"router bgp\s+(\d+)(.*?)(?=\n!|\Z)", text, re.DOTALL)
    if not bgp_match:
        return None

    as_number = bgp_match.group(1)
    bgp_block = bgp_match.group(2)

    router_id_match = re.search(r"bgp router-id\s+(\S+)", bgp_block)
    neighbors_raw = re.findall(r"neighbor\s+(\S+)\s+remote-as\s+(\d+)", bgp_block)
    timers = re.findall(r"neighbor\s+(\S+)\s+timers\s+(\d+)\s+(\d+)", bgp_block)
    networks = re.findall(r"network\s+(\S+)\s+mask\s+(\S+)", bgp_block)

    timers_by_neighbor = {n[0]: {"keepalive": n[1], "hold": n[2]} for n in timers}

    neighbors = []
    for neighbor_ip, remote_as in neighbors_raw:
        neighbors.append({
            "neighbor": neighbor_ip,
            "remote_as": remote_as,
            "timers": timers_by_neighbor.get(neighbor_ip)
        })

    return {
        "as_number": as_number,
        "router_id": router_id_match.group(1) if router_id_match else None,
        "neighbors": neighbors,
        "networks": [{"network": n[0], "mask": n[1]} for n in networks]
    }

def parse_config(text):
    return {
        "hostname": parse_hostname(text),
        "interfaces": parse_interfaces(text),
        "ospf": parse_ospf(text),
        "bgp": parse_bgp(text)
    }

def main():
    print(f"📄 Loading config: {CONFIG_PATH}")
    text = load_config(CONFIG_PATH)

    print("🔍 Parsing config...")
    result = parse_config(text)

    print("\n✅ Parsed result:\n")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()