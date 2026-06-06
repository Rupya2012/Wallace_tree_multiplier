from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


WIDTH = 32
MODULE_KEY = "wallace32_n3_5"
MAX_DEPTH = 7
BEAM_WIDTH = 2500


@dataclass
class StagePlan:
    target_max: int
    next_profile: tuple[int, ...]
    forced_visual_cols: dict[int, list[int]]
    c53: int
    c32: int
    c22: int

    @property
    def cost_tuple(self) -> tuple[int, int, int]:
        # Primary: minimize smaller compressors. Secondary: minimize c22. Tertiary: total compressors.
        return (self.c32 + self.c22, self.c22, self.c53 + self.c32 + self.c22)


@dataclass
class PathNode:
    profile: tuple[int, ...]
    cost: tuple[int, int, int]
    plans: list[StagePlan]


def _trim_profile(profile: tuple[int, ...]) -> tuple[int, ...]:
    p = list(profile)
    while len(p) > 1 and p[-1] == 0:
        p.pop()
    return tuple(p)


def _add_cost(a: tuple[int, int, int], b: tuple[int, int, int]) -> tuple[int, int, int]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _initial_profile(width: int = WIDTH) -> tuple[int, ...]:
    cols = [0] * (2 * width + 3)
    for i in range(width):
        for j in range(width):
            cols[i + j] += 1
    return _trim_profile(tuple(cols))


def _rem_options(rem: int) -> list[tuple[int, int, int]]:
    opts: list[tuple[int, int, int]] = []
    for n3 in range(rem // 3 + 1):
        rem_after_3 = rem - 3 * n3
        for n2 in range(rem_after_3 // 2 + 1):
            p = rem_after_3 - 2 * n2
            opts.append((n3, n2, p))
    return opts


def _stage_transition(profile: tuple[int, ...], target_max: int) -> StagePlan | None:
    heights = list(profile) + [0, 0]
    ncols = len(heights)

    n5 = [h // 5 for h in heights]
    rem = [h - 5 * n5c for h, n5c in zip(heights, n5)]
    carry2_fixed = [n5[c - 2] if c >= 2 else 0 for c in range(ncols)]
    options_cache = {r: _rem_options(r) for r in range(5)}

  
    dp: list[dict[int, tuple[int, int, int]]] = [dict() for _ in range(ncols + 1)]
    back: dict[tuple[int, int], tuple[int, int, int, int, int]] = {}
    dp[0][0] = (0, 0, 0)

    for c in range(ncols):
        layer = dp[c]
        next_layer: dict[int, tuple[int, int, int]] = {}
        for carry1_in, cost in layer.items():
            for n3c, n2c, passc in options_cache[rem[c]]:
                same = n5[c] + n3c + n2c + passc
                out_h = carry1_in + carry2_fixed[c] + same
                if out_h > target_max:
                    continue

                carry1_out = n5[c] + n3c + n2c
                add = (n3c + n2c, n2c, n5[c] + n3c + n2c)
                new_cost = _add_cost(cost, add)

                old = next_layer.get(carry1_out)
                if old is None or new_cost < old:
                    next_layer[carry1_out] = new_cost
                    back[(c + 1, carry1_out)] = (carry1_in, n3c, n2c, passc, out_h)
        dp[c + 1] = next_layer

    if 0 not in dp[ncols]:
        return None

    out_heights = [0] * ncols
    forced_visual_cols: dict[int, list[int]] = {}
    c32 = 0
    c22 = 0
    carry_state = 0

    for c in range(ncols - 1, -1, -1):
        prev_carry, n3c, n2c, _passc, out_h = back[(c + 1, carry_state)]
        out_heights[c] = out_h
        if n3c or n2c:
            forced_visual_cols[c + 1] = [3] * n3c + [2] * n2c
        c32 += n3c
        c22 += n2c
        carry_state = prev_carry

    c53 = sum(n5)
    next_profile = _trim_profile(tuple(out_heights))
    return StagePlan(target_max, next_profile, forced_visual_cols, c53, c32, c22)


def search_best_schedule_bfs(
    width: int = WIDTH,
    max_depth: int = MAX_DEPTH,
    beam_width: int = BEAM_WIDTH,
) -> PathNode:
    start = _initial_profile(width)
    current: dict[tuple[int, ...], PathNode] = {start: PathNode(start, (0, 0, 0), [])}

    if max(start) <= 2:
        return current[start]

    for _depth in range(1, max_depth + 1):
        next_map: dict[tuple[int, ...], PathNode] = {}

        for node in current.values():
            max_in = max(node.profile)
            for target in range(2, max_in + 1):
                plan = _stage_transition(node.profile, target)
                if plan is None:
                    continue
                new_profile = plan.next_profile
                new_cost = _add_cost(node.cost, plan.cost_tuple)
                candidate = PathNode(new_profile, new_cost, node.plans + [plan])

                old = next_map.get(new_profile)
                if old is None or candidate.cost < old.cost:
                    next_map[new_profile] = candidate

        if not next_map:
            break

        successes = [n for n in next_map.values() if max(n.profile) <= 2]
        if successes:
            return min(successes, key=lambda n: n.cost)


        ranked = sorted(next_map.values(), key=lambda n: (max(n.profile), n.cost))
        current = {n.profile: n for n in ranked[:beam_width]}

    raise RuntimeError("No <=2-row schedule found within search limits.")


def _format_override(path: PathNode, width: int = WIDTH, module_key: str = MODULE_KEY) -> str:
    stage_map: dict[int, dict[int, list[int]]] = {}
    for stage_idx, plan in enumerate(path.plans):
        if plan.forced_visual_cols:
            stage_map[stage_idx] = dict(sorted(plan.forced_visual_cols.items()))

    lines = []
    lines.append(f"phase32_start_stage = {{{width}: 99}}")
    lines.append(f"auto_use_c22_by_default = {{{width}: False}}")
    lines.append("compressor_override = {")
    lines.append(f"    {width}: {{")
    lines.append(f'        "{module_key}": {{')
    for stg in sorted(stage_map):
        lines.append(f"            {stg}: {{")
        for col in sorted(stage_map[stg]):
            lines.append(f"                {col}: {stage_map[stg][col]},")
        lines.append("            },")
    lines.append("        }")
    lines.append("    }")
    lines.append("}")
    return "\n".join(lines)


def main() -> None:
    best = search_best_schedule_bfs()
    print("Best schedule found")
    print(f"  stages: {len(best.plans)}")
    print(f"  final max height: {max(best.profile)}")
    print(f"  objective (c32+c22, c22, total_compressors): {best.cost}")
    for i, p in enumerate(best.plans):
        print(
            f"  stage {i}: target<={p.target_max}, c53={p.c53}, c32={p.c32}, c22={p.c22}, "
            f"forced_cols={len(p.forced_visual_cols)}"
        )
    print("\nSuggested extra_list.py override block:\n")
    print(_format_override(best))


if __name__ == "__main__":
    main()
