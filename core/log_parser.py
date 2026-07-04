import re
import json

LOG_PATH = "data/logs/sample_router1.log"

def load_log(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.readlines()

def parse_line(line):
    line = line.strip()
    if not line:
        return None

    # Extract timestamp + hostname prefix (common to all lines)
    header_match = re.match(r"^(\w+\s+\d+\s+\d+:\d+:\d+)\s+(\S+)\s+%(.+)", line)
    if not header_match:
        return None

    timestamp, hostname, rest = header_match.groups()

    event = {
        "timestamp": timestamp,
        "hostname": hostname,
        "raw": line,
        "type": "UNKNOWN",
        "details": {}
    }

    # OSPF adjacency change
    ospf_match = re.search(
        r"OSPF-5-ADJCHG:\s+Process (\d+), Nbr (\S+) on (\S+) from (\S+) to ([A-Z]+)(?:,\s*(.*))?",
        rest
    )
    if ospf_match:
        process_id, neighbor, interface, from_state, to_state, reason = ospf_match.groups()
        event["type"] = "OSPF_ADJACENCY_CHANGE"
        event["details"] = {
            "process_id": process_id,
            "neighbor": neighbor,
            "interface": interface,
            "from_state": from_state,
            "to_state": to_state,
            "reason": reason.strip() if reason else None,
            "severity": "critical" if to_state == "DOWN" else "info"
        }
        return event

    # Interface up/down
    link_match = re.search(r"LINK-3-UPDOWN:\s+Interface (\S+), changed state to (\w+)", rest)
    if link_match:
        interface, new_state = link_match.groups()
        event["type"] = "INTERFACE_STATE_CHANGE"
        event["details"] = {
            "interface": interface.rstrip(","),
            "new_state": new_state,
            "severity": "warning" if new_state == "down" else "info"
        }
        return event

    # BGP adjacency change
    bgp_match = re.search(r"BGP-5-ADJCHANGE:\s+neighbor (\S+) (Up|Down)(?:\s+(.*))?", rest)
    if bgp_match:
        neighbor, state, reason = bgp_match.groups()
        event["type"] = "BGP_ADJACENCY_CHANGE"
        event["details"] = {
            "neighbor": neighbor,
            "state": state,
            "reason": reason.strip() if reason else None,
            "severity": "critical" if state == "Down" else "info"
        }
        return event

    # STP / BPDU Guard events
    stp_match = re.search(r"SPANTREE-2-BLOCK_BPDUGUARD_SHUT:\s+(.+)", rest)
    if stp_match:
        detail_text = stp_match.group(1)
        event["type"] = "STP_BPDU_GUARD_SHUTDOWN"
        event["details"] = {
            "description": detail_text.strip(),
            "severity": "warning"
        }
        return event

    return event  # returns UNKNOWN type if nothing matched

def parse_log(lines):
    events = []
    for line in lines:
        parsed = parse_line(line)
        if parsed:
            events.append(parsed)
    return events

def main():
    print(f"📄 Loading log: {LOG_PATH}")
    lines = load_log(LOG_PATH)

    print("🔍 Parsing log entries...")
    events = parse_log(lines)

    print(f"\n✅ Parsed {len(events)} events:\n")
    print(json.dumps(events, indent=2))

    # Quick summary
    print("\n📊 Summary by type:")
    summary = {}
    for e in events:
        summary[e["type"]] = summary.get(e["type"], 0) + 1
    for k, v in summary.items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()