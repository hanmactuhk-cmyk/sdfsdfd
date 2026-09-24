import json
from pathlib import Path

SOCKETS = {
    "prompt": ([], ["string"]),
    "batch_prompt": ([], ["string"]),
    "reference": ([], ["image"]),
    "batch_loader": ([], ["image"]),
    "frame_extract": (["video"], ["image"]),
    "render": (["video", "video"], ["video"]),
    "generate": (["string"], ["image"]),
    "video_generate": (["string"], ["video"]),
    "grok": (["string"], ["any"]),
    "meta": (["string"], ["any"]),
    "openai": (["string"], ["image"]),
}


def _mode_inputs(node):
    node_type = node.get("type")
    mode = node.get("values", {}).get("mode")
    count = max(0, len(node.get("inputs", [])) - 1)
    if node_type == "video_generate":
        return ["string", "image", "image"] if mode == "image" else ["string"] + ["image"] * count
    if node_type == "grok":
        return ["string"] + ["image"] * count if mode in ("i2i", "i2v") else ["string"]
    if node_type == "meta":
        if mode == "i2i":
            return ["string"] + ["image"] * count
        if mode == "i2v":
            return ["string", "image", "image"]
        return ["string"]
    if node_type in ("generate", "openai"):
        return ["string"] + ["image"] * count
    return SOCKETS.get(node_type, ([], []))[0]


def validate(doc, check_files=True):
    errors, warnings = [], []
    if not isinstance(doc, dict):
        return ["Workflow root must be an object"], []
    nodes = doc.get("nodes")
    edges = doc.get("edges")
    groups = doc.get("groups", [])
    if not isinstance(nodes, list): errors.append("nodes must be an array")
    if not isinstance(edges, list): errors.append("edges must be an array")
    if not isinstance(groups, list): errors.append("groups must be an array")
    if errors:
        return errors, warnings

    ids = set()
    for i, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"node {i}: must be an object")
            continue
        for key in ("id", "type", "title", "x", "y", "inputs", "outputs", "values"):
            if key not in node:
                errors.append(f"node {i}: missing {key}")
        if node.get("id") in ids:
            errors.append(f"node {i}: duplicate id {node.get('id')}")
        ids.add(node.get("id"))
        node_type = node.get("type")
        if node_type not in SOCKETS:
            errors.append(f"node {i}: unknown type {node_type}")
            continue
        expected = _mode_inputs(node)
        if len(node.get("inputs", [])) != len(expected):
            errors.append(f"node {i}: inputs count {len(node.get('inputs', []))} != expected {len(expected)}")
        if node_type in ("prompt", "batch_prompt", "reference", "batch_loader") and node.get("inputs"):
            errors.append(f"node {i}: {node_type} must have zero inputs")
        if check_files and node_type == "reference":
            path = node.get("values", {}).get("file_path")
            if path and not Path(path).exists():
                warnings.append(f"node {i}: reference file does not exist: {path}")
        if check_files and node_type == "batch_loader":
            path = node.get("values", {}).get("file_path")
            if path and not Path(path).is_dir():
                warnings.append(f"node {i}: batch folder does not exist: {path}")

    for j, edge in enumerate(edges):
        if not isinstance(edge, dict):
            errors.append(f"edge {j}: invalid fields")
            continue
        try:
            start_node = edge["start_node"]
            start_socket = edge["start_socket"]
            end_node = edge["end_node"]
            end_socket = edge["end_socket"]
        except KeyError:
            errors.append(f"edge {j}: invalid fields")
            continue
        if not all(isinstance(x, int) for x in (start_node, start_socket, end_node, end_socket)):
            errors.append(f"edge {j}: node/socket indexes must be integers")
            continue
        if not (0 <= start_node < len(nodes) and 0 <= end_node < len(nodes)):
            errors.append(f"edge {j}: node index out of range")
            continue
        outputs = SOCKETS.get(nodes[start_node].get("type"), ([], []))[1]
        inputs = _mode_inputs(nodes[end_node])
        if start_socket < 0 or start_socket >= len(outputs):
            errors.append(f"edge {j}: start socket {start_socket} invalid")
            continue
        if end_socket < 0 or end_socket >= len(inputs):
            errors.append(f"edge {j}: end socket {end_socket} invalid")
            continue
        source_type = outputs[start_socket]
        target_type = inputs[end_socket]
        if source_type != "any" and target_type != "any" and source_type != target_type:
            errors.append(f"edge {j}: incompatible {source_type} -> {target_type}")

    incoming = set()
    for edge in edges:
        key = (edge.get("end_node"), edge.get("end_socket"))
        if key in incoming and isinstance(key[0], int) and 0 <= key[0] < len(nodes):
            inputs = _mode_inputs(nodes[key[0]])
            if isinstance(key[1], int) and 0 <= key[1] < len(inputs) and inputs[key[1]] == "string":
                errors.append(f"prompt socket {key[0]} has multiple incoming edges")
        incoming.add(key)

    graph = {i: [] for i in range(len(nodes))}
    for edge in edges:
        a, b = edge.get("start_node"), edge.get("end_node")
        if isinstance(a, int) and isinstance(b, int) and a in graph and b in graph:
            graph[a].append(b)
    state = [0] * len(nodes)
    def visit(v):
        state[v] = 1
        for w in graph[v]:
            if state[w] == 1: return True
            if state[w] == 0 and visit(w): return True
        state[v] = 2
        return False
    if any(state[i] == 0 and visit(i) for i in range(len(nodes))):
        errors.append("workflow contains a cycle")
    return errors, warnings


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(doc, path):
    Path(path).write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
