"""Minimal S-expression reader/writer for KiCad files, plus a symbol-library loader."""
import re

_tok = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+')


class Q(str):
    """A token that must be written quoted."""


def parse(text):
    stack, cur = [], []
    for m in _tok.finditer(text):
        t = m.group(0)
        if t == "(":
            stack.append(cur); cur = []
        elif t == ")":
            done = cur; cur = stack.pop(); cur.append(done)
        elif t[0] == '"':
            cur.append(Q(re.sub(r'\\(.)', lambda m: "\n" if m.group(1) == "n" else m.group(1), t[1:-1])))
        else:
            cur.append(t)
    return cur[0]


def dump(x, ind=0):
    if isinstance(x, list):
        if not any(isinstance(e, list) for e in x):
            return "(" + " ".join(dump(e) for e in x) + ")"
        head = []
        i = 0
        while i < len(x) and not isinstance(x[i], list):
            head.append(dump(x[i])); i += 1
        body = "".join("\n" + "\t" * (ind + 1) + dump(e, ind + 1) for e in x[i:])
        return "(" + " ".join(head) + body + "\n" + "\t" * ind + ")"
    if isinstance(x, Q):
        return '"' + x.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    if isinstance(x, float):
        return ("%.4f" % x).rstrip("0").rstrip(".")
    return str(x)


def find(node, key):
    return [e for e in node if isinstance(e, list) and e and e[0] == key]


def find1(node, key):
    r = find(node, key)
    return r[0] if r else None


class SymLib:
    """Loads symbols from KiCad .kicad_sym files and flattens 'extends'."""
    def __init__(self, libdir="/usr/share/kicad/symbols"):
        self.libdir, self.cache = libdir, {}

    def lib(self, name, path=None):
        if name not in self.cache:
            p = path or f"{self.libdir}/{name}.kicad_sym"
            tree = parse(open(p).read())
            self.cache[name] = {s[1]: s for s in find(tree, "symbol")}
        return self.cache[name]

    def get(self, lib, name):
        syms = self.lib(lib)
        s = syms[name]
        ext = find1(s, "extends")
        if ext:
            parent = self.get(lib, ext[1])
            props = {p[1]: p for p in find(s, "property")}
            out = [e for e in parent if not (isinstance(e, list) and e[0] in ("property",))]
            out[1] = Q(name)
            pprops = [p for p in find(parent, "property")]
            merged = [props.get(p[1], p) for p in pprops] + [p for k, p in props.items() if k not in {q[1] for q in pprops}]
            out = out[:2] + merged + out[2:]
            # rename unit sub-symbols Parent_x_y -> Name_x_y
            for e in out:
                if isinstance(e, list) and e[0] == "symbol":
                    e[1] = Q(re.sub(r"^.*(_\d+_\d+)$", name + r"\1", e[1]))
            s = out
        return s

    @staticmethod
    def pins(sym):
        """[(number, name, x, y, angle, unit, type)] for all units (unit 0 = common)."""
        out = []
        for sub in find(sym, "symbol"):
            m = re.match(r".*_(\d+)_(\d+)$", sub[1]); unit = int(m.group(1))
            for p in find(sub, "pin"):
                at = find1(p, "at")
                out.append((find1(p, "number")[1], find1(p, "name")[1], float(at[1]), float(at[2]),
                            int(float(at[3])) if len(at) > 3 else 0, unit, p[1]))
        return out
