"""
schgen.py - KiCad hierarchical schematic generator for the MEWP telematics tracker.

Emits .kicad_sch S-expression files. Symbol definitions are copied verbatim from
the KiCad 10 stock libraries and the project-local lib/jlc.kicad_sym into each
sheet's (lib_symbols) block, so every sheet is self-contained and parses without
library resolution.

Connection style: each connected pin gets a short wire stub terminated by a
label. Nets are defined by label name, not by wire geometry -- this removes a
whole class of geometry bugs from generated schematics. Cross-sheet nets use
hierarchical labels (which become sheet pins on the parent). Ground uses
power:GND symbols.

UUIDs are derived deterministically (uuid5) from stable keys, so regenerating a
sheet produces a byte-identical file and git diffs stay meaningful.
"""

import re
import os
import uuid as _uuid

KI_SYMS = r"C:\Program Files\KiCad\10.0\share\kicad\symbols"
JLC_LIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "lib", "jlc.kicad_sym")
PROJECT = "telematics-tracker"
ROOT_UUID = "784bc421-9fc7-43cb-bfc3-562714cb3f68"
NS = _uuid.UUID("11111111-2222-3333-4444-555555555555")

# Power-symbol references must be unique across the WHOLE project, not per
# sheet: two sheets both emitting #PWR001 makes KiCad conflate them, which
# shows up as bogus "pin not connected" errors. One process-wide counter.
_PWR_SEQ = [0]

# Every reference must be unique across the whole project, and every pin may
# be connected only once -- connecting a pin twice quietly parallels the two
# nets and can short a series component out of circuit.
_USED_REFS = {}
_CONNECTED_PINS = set()

SCH_VERSION = "20250610"


def _drop_balanced(text, opener):
    """Remove every balanced S-expression that starts with `opener`."""
    while True:
        i = text.find(opener)
        if i < 0:
            return text
        depth, j = 0, i
        while True:
            c = text[j]
            if c == '"':
                j += 1
                while text[j] != '"' or text[j - 1] == '\\':
                    j += 1
            elif c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    break
            j += 1
        k = i
        while k > 0 and text[k - 1] in " \t":
            k -= 1
        if k > 0 and text[k - 1] == "\n":
            k -= 1
        text = text[:k] + text[j + 1:]


def sanitize_for_schematic(block):
    """Strip tokens that are legal in a .kicad_sym but rejected inside a
    schematic's (lib_symbols). Getting this wrong makes KiCad refuse the whole
    sheet with only 'Failed to load schematic'."""
    for tok in ("show_name", "do_not_autoplace", "in_pos_files"):
        block = re.sub(r'\n[ \t]*\(' + tok + r' (?:yes|no)\)', '', block)
    # (property private ...) IS accepted inside a schematic; stripping it only
    # caused a spurious lib_symbol_mismatch warning, so it is kept verbatim.
    # easyeda2kicad declares every pin "unspecified", which makes ERC flag
    # every IC-to-passive connection as a pin conflict -- pure noise that
    # buries real findings. "passive" is the honest neutral type for a pin
    # whose direction the importer never recorded, and it conflicts with
    # nothing, so real findings stay visible.
    return block.replace("(pin unspecified ", "(pin passive ")


def det_uuid(*parts):
    return str(_uuid.uuid5(NS, "|".join(str(p) for p in parts)))


# ---------------------------------------------------------------- symbol cache

def _iter_top_symbols(text):
    """Yield (name, block_text) for each top-level (symbol "NAME" ...)."""
    for m in re.finditer(r'\n\t\(symbol "([^"]+)"', text):
        start = m.start() + 1
        depth = 0
        i = start
        while True:
            c = text[i]
            if c == '"':
                i += 1
                while text[i] != '"' or text[i - 1] == '\\':
                    i += 1
            elif c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    # lstrip: the slice starts at the leading tab, and callers
                    # rename with a '^(symbol ...' anchored pattern.
                    yield m.group(1), text[start:i + 1].lstrip()
                    break
            i += 1


class SymbolCache:
    def __init__(self):
        self._libs = {}
        self._defs = {}   # "Lib:Name" -> block text (renamed)
        self._pins = {}   # "Lib:Name" -> {number: (x, y, angle, length, name, type)}

    def _load_lib(self, lib):
        if lib in self._libs:
            return self._libs[lib]
        path = JLC_LIB if lib == "jlc" else os.path.join(KI_SYMS, lib + ".kicad_sym")
        if not os.path.exists(path):
            raise FileNotFoundError(f"symbol library not found: {path}")
        text = open(path, encoding="utf-8").read()
        self._libs[lib] = dict(_iter_top_symbols(text))
        return self._libs[lib]

    @staticmethod
    def _rename(block, old, new_top, child_base):
        """Rename a symbol block for embedding in a schematic's (lib_symbols).

        In a schematic the top-level symbol is named "Nick:Name", but its child
        unit sub-symbols must keep the BARE name ("Name_1_1", no nickname) --
        that is how KiCad matches units to their parent. Prefixing the children
        makes unit lookup fail and KiCad rejects the entire sheet with only
        "Failed to load schematic".
        """
        block = re.sub(r'^\(symbol "' + re.escape(old) + '"',
                       '(symbol "%s"' % new_top, block, count=1)
        return re.sub(r'\(symbol "' + re.escape(old) + r'_(\d+)_(\d+)"',
                      lambda m: '(symbol "%s_%s_%s"' % (child_base, m.group(1),
                                                        m.group(2)),
                      block)

    def get(self, lib_id):
        """Return (definition_block, pin_map) for 'Lib:Name'.

        Derived symbols -- those declaring (extends "BASE") -- carry no geometry
        of their own, so they are flattened onto the base symbol's graphics and
        pins. Without this they would silently place with zero pins.
        """
        if lib_id in self._defs:
            return self._defs[lib_id], self._pins[lib_id]
        lib, name = lib_id.split(":", 1)
        symbols = self._load_lib(lib)
        if name not in symbols:
            raise KeyError(f"symbol '{name}' not in library '{lib}'. "
                           f"Available sample: {sorted(symbols)[:8]}")
        block = symbols[name]

        ext = re.search(r'\(extends "([^"]+)"\)', block)
        if ext:
            base = ext.group(1)
            if base not in symbols:
                raise KeyError(f"'{name}' extends '{base}' which is missing from '{lib}'")
            block = self._rename(symbols[base], base, f"{lib}:{name}", name)
        else:
            block = self._rename(block, name, f"{lib}:{name}", name)

        # A silently-failed rename leaves the definition under its bare name
        # while instances reference "Lib:Name"; KiCad then refuses to load the
        # whole sheet with only "Failed to load schematic". Fail loudly instead.
        if not block.startswith(f'(symbol "{lib}:{name}"'):
            raise RuntimeError(
                f"rename of '{name}' -> '{lib}:{name}' failed; block starts with "
                f"{block[:60]!r}")
        bad = [n for n in re.findall(r'\(symbol "([^"]+)"', block)[1:]
               if not n.startswith(name + "_")]
        if bad:
            raise RuntimeError(
                f"{lib}:{name}: child unit symbols must be bare-named "
                f"'{name}_<unit>_<style>', got {bad}")
        block = sanitize_for_schematic(block)

        pins = {}
        for pm in re.finditer(
                r'\(pin (\w+) \w+\s*\n\s*\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)\s*\n\s*'
                r'\(length ([-\d.]+)\)[\s\S]{0,400}?\(name\s*\n?\s*"([^"]*)"'
                r'[\s\S]{0,300}?\(number\s*\n?\s*"([^"]*)"', block):
            ptype, x, y, ang, ln, pname, num = pm.groups()
            pins[num] = (float(x), float(y), float(ang), float(ln), pname, ptype)

        self._defs[lib_id] = block
        self._pins[lib_id] = pins
        return block, pins


CACHE = SymbolCache()

# outward unit vector in SCHEMATIC coords, keyed by pin angle
# pin angle points from the connection point toward the symbol body,
# and schematic Y is inverted relative to symbol Y.
_OUT = {0: (-1.0, 0.0), 90: (0.0, 1.0), 180: (1.0, 0.0), 270: (0.0, -1.0)}
_LBL_ROT = {(-1.0, 0.0): 180, (1.0, 0.0): 0, (0.0, 1.0): 270, (0.0, -1.0): 90}


def _fmt(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


class Part:
    """A placed symbol instance."""

    def __init__(self, sheet, lib_id, ref, value, at, footprint, lcsc, dnp, fields, rot):
        self.sheet, self.lib_id, self.ref, self.value = sheet, lib_id, ref, value
        self.x, self.y, self.rot = at[0], at[1], rot
        self.footprint, self.lcsc, self.dnp = footprint, lcsc, dnp
        self.fields = fields or {}
        _, self.pins = CACHE.get(lib_id)
        if not self.pins:
            raise ValueError(
                f"symbol '{lib_id}' resolved to ZERO pins (ref {ref}). A schematic "
                f"built on it would have no connections -- refusing to place.")

    def pin_xy(self, number):
        """Absolute schematic coordinate of a pin's connection point."""
        if number not in self.pins:
            raise KeyError(f"{self.ref} ({self.lib_id}) has no pin '{number}'. "
                           f"Pins: {sorted(self.pins)}")
        sx, sy, ang, _ln, _nm, _ty = self.pins[number]
        if self.rot == 0:
            return (self.x + sx, self.y - sy)
        if self.rot == 180:
            return (self.x - sx, self.y + sy)
        raise ValueError(f"unsupported rotation {self.rot} (only 0/180)")

    def pin_out(self, number):
        """Outward unit vector for a pin, in schematic coords."""
        ang = self.pins[number][2] % 360
        vx, vy = _OUT[ang]
        if self.rot == 180:
            vx, vy = -vx, -vy
        return (vx, vy)

    def pin_name(self, number):
        return self.pins[number][4]


class Sheet:
    def __init__(self, name, paper="A3", title=None):
        self.name = name
        self.paper = paper
        self.title = title or name
        self.uuid = det_uuid("sheetfile", name)
        self.sheet_symbol_uuid = det_uuid("sheetsym", name)
        self.root_level = False   # True for symbols living in the root sheet
        self.parts = []
        self.items = []          # raw S-expression strings
        self.used = []           # lib_ids in placement order
        self.hier_pins = {}      # net name -> shape
        self._n = 0
        # (x, y) -> net name, used to catch two different nets landing on the
        # same point. Such a collision silently merges the nets, which is the
        # one dangerous failure mode of label-based connection.
        self._net_pts = {}
        # stub segments as (net, x1, y1, x2, y2); collinear overlap between two
        # different nets is a short, and it is invisible to a point-only check
        self._segs = []

    # -- placement ---------------------------------------------------------
    def place(self, lib_id, ref, value, at, footprint="", lcsc="", dnp=False,
              fields=None, rot=0):
        # Everything must sit on the 1.27 mm connection grid or KiCad reports
        # endpoint_off_grid and may refuse to bind wires to pins.
        for v, axis in ((at[0], "x"), (at[1], "y")):
            if abs(round(v / 1.27) * 1.27 - v) > 1e-6:
                raise ValueError(
                    f"{ref}: {axis}={v} is off the 1.27 mm grid")
        if ref in _USED_REFS and _USED_REFS[ref] != (self.name, at):
            raise ValueError(
                f"duplicate reference '{ref}': already used on sheet "
                f"'{_USED_REFS[ref][0]}'. References must be unique "
                f"project-wide.")
        _USED_REFS[ref] = (self.name, at)
        if lib_id not in self.used:
            self.used.append(lib_id)
        p = Part(self, lib_id, ref, value, at, footprint, lcsc, dnp, fields, rot)
        self.parts.append(p)
        return p

    # -- connections -------------------------------------------------------
    def _register_seg(self, net, a, b):
        """Flag a stub that overlaps another net's stub along the same line."""
        ax, ay, bx, by = a[0], a[1], b[0], b[1]
        horiz = abs(ay - by) < 1e-6
        for (onet, ox1, oy1, ox2, oy2) in self._segs:
            if onet == net:
                continue
            ohoriz = abs(oy1 - oy2) < 1e-6
            if horiz != ohoriz:
                continue
            if horiz and abs(ay - oy1) > 1e-6:
                continue
            if not horiz and abs(ax - ox1) > 1e-6:
                continue
            lo, hi = sorted((ax, bx)) if horiz else sorted((ay, by))
            olo, ohi = sorted((ox1, ox2)) if horiz else sorted((oy1, oy2))
            if min(hi, ohi) - max(lo, olo) > 1e-6:      # true overlap
                raise ValueError(
                    f"{self.name}: stub for net '{net}' overlaps the stub for "
                    f"net '{onet}' along the same line "
                    f"({a} -> {b} vs ({ox1},{oy1}) -> ({ox2},{oy2})). "
                    f"They would short. Move the parts further apart.")
        self._segs.append((net, ax, ay, bx, by))

    def _stub(self, part, pin, length=3.81, net=None):
        key = (part.ref, pin)
        if key in _CONNECTED_PINS:
            raise ValueError(
                f"{part.ref} pin {pin} is being connected twice. The two "
                f"stubs overlap, so both nets merge -- this silently shorts "
                f"out anything in series with the pin.")
        _CONNECTED_PINS.add(key)
        x, y = part.pin_xy(pin)
        vx, vy = part.pin_out(pin)
        ex, ey = x + vx * length, y + vy * length
        if length > 0:
            self.wire((x, y), (ex, ey))
            if net is not None:
                self._register_seg(net, (x, y), (ex, ey))
        return (ex, ey), (vx, vy)

    def net(self, part, pin, name, length=3.81):
        """Stub + local label on a pin."""
        (ex, ey), v = self._stub(part, pin, length, name)
        self.label(name, (ex, ey), _LBL_ROT[v])
        return (ex, ey)

    def hier(self, part, pin, name, shape="passive", length=5.08):
        """Stub + hierarchical label on a pin (becomes a sheet pin on parent)."""
        (ex, ey), v = self._stub(part, pin, length, name)
        self.hier_label(name, (ex, ey), _LBL_ROT[v], shape)
        return (ex, ey)

    def gnd(self, part, pin, length=2.54, sym="power:GND"):
        """Stub + GND power symbol on a pin."""
        (ex, ey), v = self._stub(part, pin, length, "GND")
        self.power_at(sym, (ex, ey))
        return (ex, ey)

    def gnd_driver(self, at):
        """Declare the global GND net driven: a PWR_FLAG wired to a GND symbol.

        Needed exactly once per project. The two pins require a real wire
        between them; co-locating them is not treated as a connection.
        """
        self.power_at("power:PWR_FLAG", at)
        self.power_at("power:GND", (at[0], at[1] + 5.08))
        self.wire(at, (at[0], at[1] + 5.08))

    def nc(self, part, pin):
        x, y = part.pin_xy(pin)
        self._n += 1
        self.items.append(
            f'\t(no_connect\n\t\t(at {_fmt(x)} {_fmt(y)})\n'
            f'\t\t(uuid "{det_uuid(self.name, "nc", part.ref, pin)}")\n\t)')

    # -- primitives --------------------------------------------------------
    def wire(self, a, b):
        self._n += 1
        self.items.append(
            f'\t(wire\n\t\t(pts\n\t\t\t(xy {_fmt(a[0])} {_fmt(a[1])}) '
            f'(xy {_fmt(b[0])} {_fmt(b[1])})\n\t\t)\n'
            f'\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n'
            f'\t\t(uuid "{det_uuid(self.name, "wire", a, b, self._n)}")\n\t)')

    def junction(self, at):
        self.items.append(
            f'\t(junction\n\t\t(at {_fmt(at[0])} {_fmt(at[1])})\n\t\t(diameter 0)\n'
            f'\t\t(color 0 0 0 0)\n'
            f'\t\t(uuid "{det_uuid(self.name, "junc", at)}")\n\t)')

    def _claim(self, name, at):
        key = (round(at[0], 3), round(at[1], 3))
        prev = self._net_pts.get(key)
        if prev is not None and prev != name:
            raise ValueError(
                f"{self.name}: nets '{prev}' and '{name}' both land on "
                f"{key} -- they would silently merge into one net. "
                f"Move one of the parts.")
        self._net_pts[key] = name

    def label(self, name, at, rot=0):
        self._claim(name, at)
        self._n += 1
        just = "left bottom" if rot in (0, 90) else "right bottom"
        self.items.append(
            f'\t(label "{name}"\n\t\t(at {_fmt(at[0])} {_fmt(at[1])} {rot})\n'
            f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n'
            f'\t\t\t(justify {just})\n\t\t)\n'
            f'\t\t(uuid "{det_uuid(self.name, "lbl", name, at, self._n)}")\n\t)')

    def hier_label(self, name, at, rot=0, shape="passive"):
        self._claim(name, at)
        self._n += 1
        just = "left" if rot in (0, 90) else "right"
        self.hier_pins.setdefault(name, shape)
        self.items.append(
            f'\t(hierarchical_label "{name}"\n\t\t(shape {shape})\n'
            f'\t\t(at {_fmt(at[0])} {_fmt(at[1])} {rot})\n'
            f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n'
            f'\t\t\t(justify {just})\n\t\t)\n'
            f'\t\t(uuid "{det_uuid(self.name, "hlbl", name, at, self._n)}")\n\t)')

    def global_label(self, name, at, rot=0, shape="bidirectional"):
        """Global label: merges by name across the entire design.

        Root-level plumbing between sheet pins needs this rather than a plain
        label -- two same-named plain labels attached to sheet pins on
        different sheets are reported as dangling instead of merging.
        """
        self._claim(name, at)
        self._n += 1
        just = "left" if rot in (0, 90) else "right"
        self.items.append(
            f'\t(global_label {_sq(name)}\n\t\t(shape {shape})\n'
            f'\t\t(at {_fmt(at[0])} {_fmt(at[1])} {rot})\n'
            f'\t\t(fields_autoplaced yes)\n'
            f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n'
            f'\t\t\t(justify {just})\n\t\t)\n'
            f'\t\t(uuid "{det_uuid(self.name, "glbl", name, at, self._n)}")\n'
            f'\t\t(property "Intersheetrefs" "${{INTERSHEET_REFS}}"\n'
            f'\t\t\t(at {_fmt(at[0])} {_fmt(at[1])} 0)\n\t\t\t(hide yes)\n'
            f'\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n'
            f'\t\t\t\t(justify {just})\n\t\t\t)\n\t\t)\n\t)')

    def power_at(self, lib_id, at, value=None, rot=0):
        """Place a power symbol so its single pin sits exactly on `at`."""
        if lib_id not in self.used:
            self.used.append(lib_id)
        _, pins = CACHE.get(lib_id)
        pnum = sorted(pins)[0]
        sx, sy, _ang, _ln, _nm, _ty = pins[pnum]
        if lib_id.endswith(":GND"):
            self._claim("GND", at)
        # want origin + (sx, -sy) == at   (rot 0)
        ox, oy = at[0] - sx, at[1] + sy
        name = lib_id.split(":", 1)[1]
        self._n += 1
        _PWR_SEQ[0] += 1
        ref = f"#PWR{_PWR_SEQ[0]:03d}"
        p = Part(self, lib_id, ref, value or name, (ox, oy), "", "", False, None, rot)
        p._is_power = True
        self.parts.append(p)
        return p

    def text(self, s, at, size=1.27):
        self._n += 1
        self.items.append(
            f'\t(text {_sq(s)}\n\t\t(exclude_from_sim no)\n'
            f'\t\t(at {_fmt(at[0])} {_fmt(at[1])} 0)\n'
            f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size {size} {size})\n\t\t\t)\n'
            f'\t\t\t(justify left bottom)\n\t\t)\n'
            f'\t\t(uuid "{det_uuid(self.name, "txt", s, at)}")\n\t)')

    # -- helpers for common two-terminal chains ----------------------------
    def series(self, lib_id, ref, value, at, net_a, net_b, footprint="", lcsc="",
               dnp=False, gnd_b=False, fields=None):
        """Place a 2-pin part vertically; pin1 -> net_a, pin2 -> net_b (or GND)."""
        p = self.place(lib_id, ref, value, at, footprint, lcsc, dnp, fields)
        self.net(p, "1", net_a)
        if gnd_b:
            self.gnd(p, "2")
        else:
            self.net(p, "2", net_b)
        return p

    # -- emit --------------------------------------------------------------
    def _emit_part(self, p):
        is_power = getattr(p, "_is_power", False)
        props = []
        ref_dy = -5.08 if is_power else 0.0
        props.append(("Reference", p.ref, ref_dy, True))
        props.append(("Value", p.value, 0.0, not is_power))
        if not is_power:
            props.append(("Footprint", p.footprint, 0.0, False))
            props.append(("Datasheet", "~", 0.0, False))
            if p.lcsc:
                props.append(("LCSC", p.lcsc, 0.0, False))
            for k, v in (p.fields or {}).items():
                props.append((k, v, 0.0, False))

        out = ['\t(symbol', f'\t\t(lib_id "{p.lib_id}")',
               f'\t\t(at {_fmt(p.x)} {_fmt(p.y)} {p.rot})', '\t\t(unit 1)',
               '\t\t(exclude_from_sim no)',
               # Power symbols must be in_bom/on_board yes, exactly as KiCad
               # writes them: marking them "no" excludes them from the netlist
               # and their pins then read as unconnected. Their "#"-prefixed
               # references keep them out of the real BOM anyway.
               '\t\t(in_bom yes)',
               '\t\t(on_board yes)',
               f'\t\t(dnp {"yes" if p.dnp else "no"})',
               '\t\t(fields_autoplaced yes)',
               f'\t\t(uuid "{det_uuid(self.name, "sym", p.ref)}")']
        for i, (k, v, dy, shown) in enumerate(props):
            hide = "" if shown else "\n\t\t\t(hide yes)"
            py = p.y + dy - (2.54 + i * 2.54 if shown else 0)
            out.append(
                f'\t\t(property "{k}" {_sq(v)}\n'
                f'\t\t\t(at {_fmt(p.x)} {_fmt(py)} 0){hide}\n'
                f'\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n'
                f'\t\t\t)\n\t\t)')
        for num in sorted(p.pins, key=lambda n: (len(n), n)):
            out.append(f'\t\t(pin "{num}"\n\t\t\t'
                       f'(uuid "{det_uuid(self.name, "pin", p.ref, num)}")\n\t\t)')
        path = (f"/{ROOT_UUID}" if self.root_level
                else f"/{ROOT_UUID}/{self.sheet_symbol_uuid}")
        out.append('\t\t(instances')
        out.append(f'\t\t\t(project "{PROJECT}"')
        out.append(f'\t\t\t\t(path "{path}"')
        out.append(f'\t\t\t\t\t(reference "{p.ref}")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)')
        out.append('\t\t\t)\n\t\t)\n\t)')
        return "\n".join(out)

    def render(self):
        lib_blocks = []
        for lib_id in self.used:
            block, _ = CACHE.get(lib_id)
            lib_blocks.append("\n".join("\t\t" + ln if ln.strip() else ln
                                        for ln in block.split("\n")))
        body = [
            "(kicad_sch",
            f'\t(version {SCH_VERSION})',
            '\t(generator "schgen.py")',
            '\t(generator_version "9.0")',
            f'\t(uuid "{self.uuid}")',
            f'\t(paper "{self.paper}")',
            "\t(lib_symbols",
            "\n".join(lib_blocks),
            "\t)",
        ]
        body.extend(self.items)
        body.extend(self._emit_part(p) for p in self.parts)
        body.append("\t(embedded_fonts no)")
        body.append(")")
        return "\n".join(body) + "\n"

    def write(self, directory):
        path = os.path.join(directory, self.name + ".kicad_sch")
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(self.render())
        return path


def _sq(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


# ------------------------------------------------------------------ root sheet

def write_root(directory, sheets, rails=(), notes=()):
    """Write the root schematic containing one sheet symbol per child sheet.

    Each child sheet pin gets a stub + local label of the same name at root
    level, so identically-named pins on different sheets form one net.
    """
    items = []
    parts_txt = []
    SH_W = 44.45
    # Sheet origins must sit on the 1.27 mm connection grid, otherwise every
    # sheet pin lands off-grid and KiCad refuses to bind wires to it.
    col_x = [25.4, 127.0, 228.6, 330.2]

    for idx, sh in enumerate(sheets):
        pins = sorted(sh.hier_pins.items())
        h = max(20.32, 2.54 * (len(pins) + 2))
        x, y = col_x[idx % 4], 25.4
        uid = sh.sheet_symbol_uuid
        s = ['\t(sheet',
             f'\t\t(at {_fmt(x)} {_fmt(y)})',
             f'\t\t(size {_fmt(SH_W)} {_fmt(h)})',
             '\t\t(fields_autoplaced yes)',
             '\t\t(stroke\n\t\t\t(width 0.1524)\n\t\t\t(type solid)\n\t\t)',
             '\t\t(fill\n\t\t\t(color 0 0 0 0.0000)\n\t\t)',
             f'\t\t(uuid "{uid}")',
             f'\t\t(property "Sheetname" {_sq(sh.name)}\n'
             f'\t\t\t(at {_fmt(x)} {_fmt(y - 0.7)} 0)\n'
             f'\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n'
             f'\t\t\t\t(justify left bottom)\n\t\t\t)\n\t\t)',
             f'\t\t(property "Sheetfile" {_sq(sh.name + ".kicad_sch")}\n'
             f'\t\t\t(at {_fmt(x)} {_fmt(y + h + 1.4)} 0)\n'
             f'\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n'
             f'\t\t\t\t(justify left top)\n\t\t\t)\n\t\t)']
        for i, (net, shape) in enumerate(pins):
            py = y + 2.54 * (i + 1)
            s.append(f'\t\t(pin {_sq(net)} {shape}\n'
                     f'\t\t\t(at {_fmt(x)} {_fmt(py)} 180)\n'
                     f'\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n'
                     f'\t\t\t\t(justify right)\n\t\t\t)\n'
                     f'\t\t\t(uuid "{det_uuid("rootpin", sh.name, net)}")\n\t\t)')
            # stub + label to the left of the sheet body
            ax, ay = x, py
            bx = x - 7.62
            items.append(
                f'\t(wire\n\t\t(pts\n\t\t\t(xy {_fmt(ax)} {_fmt(ay)}) '
                f'(xy {_fmt(bx)} {_fmt(ay)})\n\t\t)\n'
                f'\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n'
                f'\t\t(uuid "{det_uuid("rootwire", sh.name, net)}")\n\t)')
            items.append(
                f'\t(global_label {_sq(net)}\n\t\t(shape {shape})\n'
                f'\t\t(at {_fmt(bx)} {_fmt(ay)} 180)\n'
                f'\t\t(fields_autoplaced yes)\n'
                f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n'
                f'\t\t\t(justify right)\n\t\t)\n'
                f'\t\t(uuid "{det_uuid("rootlbl", sh.name, net)}")\n'
                f'\t\t(property "Intersheetrefs" "${{INTERSHEET_REFS}}"\n'
                f'\t\t\t(at {_fmt(bx)} {_fmt(ay)} 0)\n\t\t\t(hide yes)\n'
                f'\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n'
                f'\t\t\t\t(justify right)\n\t\t\t)\n\t\t)\n\t)')
        s.append('\t\t(instances')
        s.append(f'\t\t\t(project "{PROJECT}"')
        s.append(f'\t\t\t\t(path "/{ROOT_UUID}"\n\t\t\t\t\t(page "{idx + 2}")\n\t\t\t\t)')
        s.append('\t\t\t)\n\t\t)\n\t)')
        parts_txt.append("\n".join(s))

    # Rails that will be driven by power.kicad_sch (not yet drawn) get a
    # PWR_FLAG here so they are not reported as dangling/undriven. These are
    # temporary scaffolding, removed when the power sheet lands.
    flag_sheet = Sheet("__root_flags__")
    flag_sheet.root_level = True
    for i, rail in enumerate(rails):
        fx = 25.4 + i * 20.32
        fy2 = 269.24
        flag_sheet.power_at("power:PWR_FLAG", (fx, fy2))
        items.append(
            f'\t(wire\n\t\t(pts\n\t\t\t(xy {_fmt(fx)} {_fmt(fy2)}) '
            f'(xy {_fmt(fx)} {_fmt(fy2 + 5.08)})\n\t\t)\n'
            f'\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n'
            f'\t\t(uuid "{det_uuid("railwire", rail)}")\n\t)')
        items.append(
            f'\t(label {_sq(rail)}\n\t\t(at {_fmt(fx)} {_fmt(fy2 + 5.08)} 270)\n'
            f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n'
            f'\t\t\t(justify left bottom)\n\t\t)\n'
            f'\t\t(uuid "{det_uuid("raillbl", rail)}")\n\t)')
    for j, note in enumerate(notes):
        flag_sheet.text(note, (25.4, 200.66 + j * 5.08))

    out = ["(kicad_sch",
           f'\t(version {SCH_VERSION})',
           '\t(generator "schgen.py")',
           '\t(generator_version "9.0")',
           f'\t(uuid "{ROOT_UUID}")',
           '\t(paper "A3")',
           "\t(lib_symbols"]
    for lib_id in flag_sheet.used:
        block, _ = CACHE.get(lib_id)
        out.append("\n".join("\t\t" + ln if ln.strip() else ln
                             for ln in block.split("\n")))
    out.append("\t)")
    out.extend(items)
    out.extend(flag_sheet.items)
    out.extend(flag_sheet._emit_part(p) for p in flag_sheet.parts)
    out.extend(parts_txt)
    out.append('\t(sheet_instances')
    out.append('\t\t(path "/"\n\t\t\t(page "1")\n\t\t)')
    for idx, sh in enumerate(sheets):
        out.append(f'\t\t(path "/{sh.sheet_symbol_uuid}"'
                   f'\n\t\t\t(page "{idx + 2}")\n\t\t)')
    out.append('\t)')
    out.append("\t(embedded_fonts no)")
    out.append(")")
    path = os.path.join(directory, PROJECT + ".kicad_sch")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out) + "\n")
    return path
