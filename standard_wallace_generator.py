from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from random import Random
from typing import Iterable

from a import export_pdf_and_delete_images, matrix_to_tick_cross_png

WIDTH = 16
PRODUCT_WIDTH = 2 * WIDTH


@dataclass(frozen=True)
class Instance:
    kind: str
    stage: int
    column: int
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]


@dataclass
class StageReport:
    stage: int
    input_heights: dict[int, int]
    output_heights: dict[int, int]
    boxes: list[tuple[int, int, int]] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)


@dataclass
class ReductionResult:
    columns: dict[int, list[str]]
    instances: list[Instance]
    stages: list[StageReport]
    row0: list[str | None]
    row1: list[str | None]


class NameFactory:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.names: set[str] = set()

    def new(self, prefix: str) -> str:
        idx = self.counts.get(prefix, 0)
        self.counts[prefix] = idx + 1
        name = f"{prefix}_{idx}"
        if name in self.names:
            raise ValueError(f"duplicate signal name generated: {name}")
        self.names.add(name)
        return name

    def register(self, name: str) -> None:
        if name in self.names:
            raise ValueError(f"duplicate signal name registered: {name}")
        self.names.add(name)


def initial_columns(width: int = WIDTH) -> dict[int, list[str]]:
    columns: dict[int, list[str]] = {}
    for i in range(width):
        for j in range(width):
            columns.setdefault(i + j, []).append(f"pp_{i}_{j}")
    return columns


def _ordered_columns(columns: dict[int, list[str]]) -> Iterable[int]:
    if not columns:
        return range(0)
    return range(max(columns) + 3)


def _heights(columns: dict[int, list[str]]) -> dict[int, int]:
    return {col: len(bits) for col, bits in sorted(columns.items()) if bits}


def _add_output(next_columns: dict[int, list[str]], column: int, signal: str) -> None:
    next_columns.setdefault(column, []).append(signal)


def _make_box(stage_boxes: list[tuple[int, int, int]], column: int, start_row: int, size: int) -> None:
    stage_boxes.append((column + 1, start_row + 1, size))


def reduce_wallace_standard(width: int = WIDTH) -> ReductionResult:
    names = NameFactory()
    columns = initial_columns(width)
    for bits in columns.values():
        for bit in bits:
            names.register(bit)

    instances: list[Instance] = []
    stages: list[StageReport] = []
    stage = 0

    while max((len(bits) for bits in columns.values()), default=0) > 2:
        next_columns: dict[int, list[str]] = {}
        stage_boxes: list[tuple[int, int, int]] = []
        stage_counts = {"c32": 0, "c22": 0, "pass": 0}
        input_heights = _heights(columns)

        for column in _ordered_columns(columns):
            bits = list(columns.get(column, []))
            cursor = 0

            while len(bits) - cursor >= 3:
                ins = tuple(bits[cursor : cursor + 3])
                out0 = names.new(f"s{stage}_c{column}_32_s")
                out1 = names.new(f"s{stage}_c{column}_32_c")
                _make_box(stage_boxes, column, cursor, 3)
                _add_output(next_columns, column, out0)
                _add_output(next_columns, column + 1, out1)
                instances.append(Instance("c32", stage, column, ins, (out0, out1)))
                stage_counts["c32"] += 1
                cursor += 3

            remaining = len(bits) - cursor
            needs_c22 = remaining == 2 and len(next_columns.get(column, [])) + 2 > 2
            if needs_c22:
                ins = tuple(bits[cursor : cursor + 2])
                out0 = names.new(f"s{stage}_c{column}_22_s")
                out1 = names.new(f"s{stage}_c{column}_22_c")
                _make_box(stage_boxes, column, cursor, 2)
                _add_output(next_columns, column, out0)
                _add_output(next_columns, column + 1, out1)
                instances.append(Instance("c22", stage, column, ins, (out0, out1)))
                stage_counts["c22"] += 1
                cursor += 2

            for bit in bits[cursor:]:
                _make_box(stage_boxes, column, cursor, 1)
                _add_output(next_columns, column, bit)
                stage_counts["pass"] += 1
                cursor += 1

        stages.append(
            StageReport(
                stage=stage,
                input_heights=input_heights,
                output_heights=_heights(next_columns),
                boxes=stage_boxes,
                counts=stage_counts,
            )
        )
        columns = {col: bits for col, bits in next_columns.items() if bits}
        stage += 1

    row0: list[str | None] = [None] * (2 * width)
    row1: list[str | None] = [None] * (2 * width)
    for column, bits in columns.items():
        if column < 2 * width:
            if len(bits) >= 1:
                row0[column] = bits[0]
            if len(bits) >= 2:
                row1[column] = bits[1]

    return ReductionResult(columns, instances, stages, row0, row1)


def write_report(result: ReductionResult, path: str | Path, width: int = WIDTH) -> None:
    path = Path(path)
    final_heights = _heights(result.columns)
    max_final_height = max(final_heights.values(), default=0)
    high_columns = {col: bits for col, bits in result.columns.items() if col >= 2 * width and bits}

    with path.open("w", encoding="utf-8") as f:
        f.write(f"Reduction report: standard_wallace_3to2_2to2, {width}x{width}\n")
        f.write(f"Stages: {len(result.stages)}\n")
        f.write(f"Instances: {len(result.instances)}\n")
        f.write(f"Final max column height: {max_final_height}\n")
        f.write(f"Final height <= 2: {max_final_height <= 2}\n")
        f.write(f"Signals beyond product width [{2 * width - 1}:0]: {sum(len(v) for v in high_columns.values())}\n\n")

        f.write("Stage summary\n")
        for stage in result.stages:
            max_in = max(stage.input_heights.values(), default=0)
            max_out = max(stage.output_heights.values(), default=0)
            counts = stage.counts
            f.write(
                f"Stage {stage.stage}: max_in={max_in}, max_out={max_out}, "
                f"c32={counts.get('c32', 0)}, c22={counts.get('c22', 0)}, pass={counts.get('pass', 0)}\n"
            )

        f.write("\nFinal column heights\n")
        for col in range(2 * width):
            f.write(f"  col {col}: {len(result.columns.get(col, []))}\n")

        if high_columns:
            f.write("\nHigh columns\n")
            for col, bits in sorted(high_columns.items()):
                f.write(f"  col {col}: {len(bits)}\n")

        f.write("\nPhase boxes\n")
        for stage in result.stages:
            f.write(f"Phase {stage.stage}\n")
            f.write("(\n")
            for idx, box in enumerate(stage.boxes):
                comma = "," if idx < len(stage.boxes) - 1 else ""
                f.write(f"  ({box[0]}, {box[1]}, {box[2]}){comma}\n")
            f.write(")\n\n")


def _matrix_from_heights(heights: dict[int, int], total_cols: int) -> list[list[int]]:
    row_count = max(heights.values(), default=1)
    matrix = [[0 for _ in range(total_cols)] for _ in range(row_count)]
    for col, height in heights.items():
        if 0 <= col < total_cols:
            for row in range(height):
                matrix[row][col] = 1
    return matrix


def _single_bit_columns(heights: dict[int, int], total_cols: int) -> list[int]:
    values = [0] * total_cols
    for col, height in heights.items():
        if 0 <= col < total_cols and height == 1:
            values[col] = 1
    for col in range(total_cols - 2, -1, -1):
        values[col] = min(values[col], values[col + 1])
    return values


def write_pdf(result: ReductionResult, path: str | Path, width: int = WIDTH) -> None:
    path = Path(path)
    max_input_col = max((col for stage in result.stages for col in stage.input_heights), default=2 * width - 1)
    max_box_col = max((box[0] - 1 for stage in result.stages for box in stage.boxes), default=2 * width - 1)
    total_cols = max(2 * width, max_input_col + 1, max_box_col + 1)
    image_paths: list[str] = []
    phase_box_counts: list[dict[int, int]] = []
    stem = path.with_suffix("").name

    for stage in result.stages:
        matrix = _matrix_from_heights(stage.input_heights, total_cols)
        output_values = _single_bit_columns(stage.input_heights, total_cols)
        image_path = f"{stem}_phase_{stage.stage}.png"
        matrix_to_tick_cross_png(
            matrix,
            output_path=image_path,
            vertical_boxes=stage.boxes,
            output_values=output_values,
            phase_i=stage.stage,
        )
        image_paths.append(image_path)
        phase_box_counts.append({size: sum(1 for _, _, box_size in stage.boxes if box_size == size) for size in range(2, 8)})

    if image_paths:
        export_pdf_and_delete_images(image_paths, pdf_path=str(path), phase_box_counts=phase_box_counts)


def _module_name(width: int = WIDTH) -> str:
    return f"wallace{width}_standard"


def _wire_decl(signals: list[str], chunk: int = 8) -> list[str]:
    lines: list[str] = []
    for i in range(0, len(signals), chunk):
        lines.append("wire " + ", ".join(signals[i : i + chunk]) + ";")
    return lines


def _emit_comp32() -> list[str]:
    return [
        "module comp32(input a, input b, input c, output sum, output carry);",
        "assign sum = a ^ b ^ c;",
        "assign carry = (a & b) | (a & c) | (b & c);",
        "endmodule",
    ]


def _emit_comp22() -> list[str]:
    return [
        "module comp22(input a, input b, output sum, output carry);",
        "assign sum = a ^ b;",
        "assign carry = a & b;",
        "endmodule",
    ]


def write_verilog(result: ReductionResult, path: str | Path, width: int = WIDTH) -> None:
    path = Path(path)
    module_name = _module_name(width)
    produced = {out for inst in result.instances for out in inst.outputs}
    pp_signals = [f"pp_{i}_{j}" for i in range(width) for j in range(width)]
    internal = sorted(produced)

    lines: list[str] = []
    lines.append("// Auto-generated by standard_wallace_generator.py")
    lines.append(f"module {module_name}(")
    lines.append(f"    input  [{width - 1}:0] a,")
    lines.append(f"    input  [{width - 1}:0] b,")
    lines.append(f"    output [{2 * width - 1}:0] row0,")
    lines.append(f"    output [{2 * width - 1}:0] row1")
    lines.append(");")
    lines.append("")
    lines.extend(_wire_decl(pp_signals))
    if internal:
        lines.extend(_wire_decl(internal))
    lines.append("")

    for i in range(width):
        for j in range(width):
            lines.append(f"assign pp_{i}_{j} = a[{i}] & b[{j}];")
    lines.append("")

    for idx, inst in enumerate(result.instances):
        if inst.kind == "c32":
            a, b, c = inst.inputs
            s, carry = inst.outputs
            lines.append(f"comp32 u_{idx} (.a({a}), .b({b}), .c({c}), .sum({s}), .carry({carry}));")
        elif inst.kind == "c22":
            a, b = inst.inputs
            s, carry = inst.outputs
            lines.append(f"comp22 u_{idx} (.a({a}), .b({b}), .sum({s}), .carry({carry}));")
        else:
            raise ValueError(f"unknown instance kind: {inst.kind}")
    lines.append("")

    for col in range(2 * width):
        row0_sig = result.row0[col] or "1'b0"
        row1_sig = result.row1[col] or "1'b0"
        lines.append(f"assign row0[{col}] = {row0_sig};")
        lines.append(f"assign row1[{col}] = {row1_sig};")

    high_bits = [bit for col, bits in sorted(result.columns.items()) if col >= 2 * width for bit in bits]
    lines.append("")
    if high_bits:
        lines.append("wire high_product_width_activity;")
        lines.append("assign high_product_width_activity = " + " | ".join(high_bits) + ";")
        lines.append("`ifndef SYNTHESIS")
        lines.append("always @* begin")
        lines.append("    if (high_product_width_activity) begin")
        lines.append(
            f'        $error("Unexpected activity above product width [{2 * width - 1}:0] in {module_name}");'
        )
        lines.append("    end")
        lines.append("end")
        lines.append("`endif")
    else:
        lines.append("// No activity above product width.")

    lines.append("endmodule")
    lines.append("")
    lines.extend(_emit_comp32())
    lines.append("")
    lines.extend(_emit_comp22())
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def _eval_instance(values: dict[str, int], inst: Instance) -> None:
    ins = [values[name] for name in inst.inputs]
    count = sum(ins)
    if inst.kind == "c32":
        values[inst.outputs[0]] = count & 1
        values[inst.outputs[1]] = (count >> 1) & 1
    elif inst.kind == "c22":
        values[inst.outputs[0]] = count & 1
        values[inst.outputs[1]] = (count >> 1) & 1
    else:
        raise ValueError(f"unknown instance kind: {inst.kind}")


def evaluate_rows(result: ReductionResult, a: int, b: int, width: int = WIDTH) -> tuple[int, int, dict[int, int]]:
    mask = (1 << width) - 1
    a &= mask
    b &= mask
    values: dict[str, int] = {}
    for i in range(width):
        for j in range(width):
            values[f"pp_{i}_{j}"] = ((a >> i) & 1) & ((b >> j) & 1)

    for inst in result.instances:
        _eval_instance(values, inst)

    row0 = 0
    row1 = 0
    for col, sig in enumerate(result.row0):
        if sig is not None and values[sig]:
            row0 |= 1 << col
    for col, sig in enumerate(result.row1):
        if sig is not None and values[sig]:
            row1 |= 1 << col

    high_values: dict[int, int] = {}
    for col, bits in result.columns.items():
        if col >= 2 * width:
            high_values[col] = sum(values[bit] for bit in bits)
    return row0, row1, high_values


def verify_result(result: ReductionResult, width: int = WIDTH, random_tests: int = 200) -> None:
    max_height = max((len(bits) for bits in result.columns.values()), default=0)
    if max_height > 2:
        raise AssertionError(f"final column height is {max_height}, expected <= 2")

    for inst in result.instances:
        if inst.kind == "c32":
            if len(inst.inputs) != 3 or len(inst.outputs) != 2:
                raise AssertionError(f"bad c32 instance shape: {inst}")
        elif inst.kind == "c22":
            if len(inst.inputs) != 2 or len(inst.outputs) != 2:
                raise AssertionError(f"bad c22 instance shape: {inst}")
        else:
            raise AssertionError(f"unknown instance kind: {inst}")

    tests = [
        (0, 0),
        (1, 0),
        (0, 1),
        (1, 1),
        ((1 << width) - 1, 1),
        (1, (1 << width) - 1),
        ((1 << width) - 1, (1 << width) - 1),
        (0xAAAA & ((1 << width) - 1), 0x5555 & ((1 << width) - 1)),
    ]
    rng = Random(12345)
    mask = (1 << width) - 1
    tests.extend((rng.getrandbits(width), rng.getrandbits(width)) for _ in range(random_tests))

    for a, b in tests:
        row0, row1, high = evaluate_rows(result, a, b, width)
        if any(high.values()):
            raise AssertionError(f"high product-width signal became 1 for a={a:#x}, b={b:#x}: {high}")
        got = row0 + row1
        want = (a & mask) * (b & mask)
        if got != want:
            raise AssertionError(f"bad product for a={a:#x}, b={b:#x}: got {got:#x}, want {want:#x}")


def generate_all(width: int = WIDTH, random_tests: int = 200) -> ReductionResult:
    result = reduce_wallace_standard(width=width)
    verify_result(result, width=width, random_tests=random_tests)
    write_report(result, f"matrix_phases_standard_{width}bit.txt", width=width)
    write_pdf(result, f"matrix_phases_standard_{width}bit.pdf", width=width)
    write_verilog(result, f"wallace{width}_standard.v", width=width)
    return result


if __name__ == "__main__":
    generate_all()
