# Optimizing a 16-bit Wallace Multiplier Using 5:3 Compressors and BFS Reduction

## Abstract

This project compares three 16-bit multiplier implementations: a standard Wallace tree, a plain Wallace-style reduction using 5:3 compressors, and a BFS-optimized 5:3 compressor reduction. The goal was not only to reduce the longest combinational path, but also to understand the cost of each architectural decision in area, routing, and power after physical implementation.

The design flow began with a normal standard Wallace reduction. That gave a correct and compact baseline, but the critical path was still high. The next step was to introduce 5:3 compressors so that more partial-product bits could be reduced in fewer stages. This reduced delay, but it also increased hardware and routing cost. The final step was to use a BFS-based reduction search, where the reduction matrix is explored phase by phase to reach the required two-row form with fewer unnecessary compressor placements.

All three designs use a Kogge-Stone adder as the final adder after the reduction tree has compressed the partial-product matrix to two rows.

## Design Journey

The first implementation used a standard Wallace reduction. This follows the usual idea of reducing partial products column by column with 3:2 compressor behavior until only two rows remain. It is a strong baseline because it is simple, predictable, and area-efficient.

After observing the delay of the standard reduction, the next idea was to reduce the number of reduction phases by using 5:3 compressors. A 5:3 compressor consumes five same-weight inputs and produces three outputs, allowing a taller column to shrink faster than with only 3:2 reductions. This plain 5:3 version improved the critical path from `9.1405 ns` to `8.9615 ns`.

The problem was that using 5:3 compressors freely can create more hardware than necessary. Even if delay improves, the design may pay for it through extra cells, longer wires, more vias, and higher physical complexity. That led to the BFS-optimized version. Instead of greedily placing compressors, the reduction is treated as a search problem: find a valid sequence of reduction phases that reaches two rows while avoiding unnecessary compressor use.

The optimized 5:3 design reached the best observed critical path of `8.8064 ns`. It also reduced area, routing, and power compared with the plain 5:3 version.

## Architecture

Each multiplier starts from the same high-level structure:

1. Generate the 16-bit by 16-bit partial-product matrix.
2. Reduce the matrix using compressor stages.
3. Stop when the matrix has only two rows left.
4. Feed the final two rows into a Kogge-Stone adder.
5. Produce the final 32-bit product output.

The standard Wallace version mainly uses ordinary Wallace-style reduction with 3:2 compressor behavior. The plain 5:3 version adds 5:3 compressors to reduce taller columns more aggressively. The BFS-optimized version still uses 5:3, 3:2, and 2:2 reduction elements, but chooses their placement through a search over valid matrix states.

### Custom 5:3 Compressor Structure

TODO: Insert 5:3 compressor structure diagram and explanation here.

This section should show the exact internal structure of the custom 5:3 compressor used in the project. The report can then connect that structure to the reduction-stage results below.

## BFS Reduction Method

The BFS version optimizes the reduction schedule, not the logic equations inside each compressor. The key idea is to view the partial-product matrix only by **column heights**.

For a 16-bit multiplier, each column has a binary weight. Column `0` represents weight `2^0`, column `1` represents weight `2^1`, column `2` represents weight `2^2`, and so on. At the start, the partial products form a triangle of column heights:

```text
1, 2, 3, 4, ..., 15, 16, 15, ..., 4, 3, 2, 1
```

The goal of reduction is to make every column height at most `2`. Once that happens, the multiplier has two remaining rows, which can be added by the final Kogge-Stone adder.

### How Weight Is Preserved

The compressors do not change the value of the multiplier. They only move information between columns while preserving binary weight.

A `3:2` compressor in column `c` consumes three bits of weight `2^c`. It produces:

- one sum bit back into column `c`
- one carry bit into column `c + 1`

A `2:2` compressor behaves similarly for two input bits:

- one sum bit into column `c`
- one carry bit into column `c + 1`

A `5:3` compressor consumes five bits from column `c`. Since the count of five input bits can range from `0` to `5`, the output needs three binary bits. Those outputs are assigned as:

- `s0` into column `c`
- `s1` into column `c + 1`
- `s2` into column `c + 2`

This is why the optimizer cannot look at one column alone. A compressor selected in column `c` can increase the height of later columns. The search has to account for these reassigned outputs.

### Why BFS Is Used

BFS is used because each BFS level represents one full reduction phase. A shorter BFS depth means fewer reduction phases, which is directly related to the number of compressor layers on the combinational path.

The search starts from the initial column-height profile. Then it asks:

```text
After 1 reduction phase, can every column be <= 2?
If not, after 2 phases?
If not, after 3 phases?
...
```

The first BFS depth that reaches a profile where all columns have height `<= 2` gives the minimum number of reduction phases under the explored compressor rules.

### Why DP Is Used Inside Each BFS Step

Inside one reduction phase, there is still a smaller optimization problem. For each column, the reducer must decide how to handle the leftover bits after applying `5:3` compressors:

- use a `3:2` compressor
- use a `2:2` compressor
- pass bits forward unchanged

The implementation first uses the maximum possible number of `5:3` compressors in each column. For example, if a column has height `13`, it uses two `5:3` compressors and leaves `3` remaining bits. The DP then decides whether those remaining bits should become a `3:2`, a `2:2`, or simple pass-through bits.

DP is needed because each column receives outputs from previous columns. In the code, the output height of a column is calculated from:

```text
same-column outputs
+ carry from column c - 1
+ second-level carry from column c - 2
```

If that output height is larger than the selected target height for the phase, that choice is rejected. This prevents the optimizer from reducing one column aggressively while accidentally making a later column too tall.

### What Is Minimized

For every possible next-stage target height, the DP keeps the cheapest valid transition. The cost used by the optimizer is:

```text
(number of 3:2 + 2:2 compressors,
 number of 2:2 compressors,
 total number of compressors)
```

So the priority is:

1. use fewer small cleanup compressors overall
2. among those, use fewer `2:2` compressors
3. among those, use fewer total compressors

This does not mean the optimizer avoids `5:3` compressors. The design still uses `5:3` compressors aggressively for fast height reduction. The optimization is mainly about avoiding unnecessary `3:2` and `2:2` compressors that would increase area and routing without helping the phase count.

The final BFS/DP flow is:

```text
1. Represent the matrix as column heights.
2. Search over reduction phases using BFS.
3. For each possible next-stage target height:
   a. Use maximum 5:3 compressors in each column.
   b. Use DP to choose 3:2, 2:2, or pass-through for leftovers.
   c. Reject choices that make any output column too tall.
   d. Keep the lowest-cost valid transition.
4. Stop when all columns have height <= 2.
5. Print forced compressor placements for the real Verilog generator.
```

The printed compressor placements are stored as overrides for the generator. The generator then follows those forced placements while producing the optimized 5:3 Wallace multiplier.

## Top-Level Result Summary

| Design | Critical Path | From -> To | Synthesis Area | Post-PnR Stdcell Area | Core Area | Routed Wirelength | Vias | Total Power |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| Standard Wallace | 9.1405 ns | a[4] -> sum[30] | 13919.6 | 14392.6 | 27629.0 | 36080 | 11125 | 4.396029e-3 |
| Plain 5:3, no BFS | 8.9615 ns | a[6] -> sum[28] | 15084.4672 | 15612.5 | 29717.3 | 41659 | 13439 | 2.062736e-3 |
| BFS optimized 5:3 | 8.8064 ns | a[5] -> sum[29] | 14822.9664 | 15351.0 | 29480.8 | 39773 | 13148 | 1.815034e-3 |

The plain 5:3 design improves the critical path by about `1.96%` over the standard Wallace design. The BFS-optimized 5:3 version improves the critical path by about `3.66%` over the standard design and about `1.73%` over the plain 5:3 version.

The 5:3 designs are not smaller than the standard Wallace design. Both 5:3 versions use more area and routing resources than the standard baseline. The useful result is more specific: BFS improves the 5:3 architecture itself. Compared with the plain 5:3 design, the BFS version reduces synthesis area by about `1.73%`, routed wirelength by about `4.53%`, vias by about `2.17%`, and total power by about `12.0%`.

## Critical Path Comparison

### Standard Wallace

The standard Wallace multiplier has the longest observed combinational path:

| Rank | Delay (ns) | From | To |
|---:|---:|---|---|
| 1 | 9.1405 | a[4] | sum[30] |
| 2 | 9.1249 | a[4] | sum[24] |
| 3 | 9.0602 | a[4] | sum[28] |
| 4 | 8.8850 | a[4] | sum[26] |
| 5 | 8.6056 | a[4] | sum[22] |
| 6 | 8.4798 | a[7] | sum[29] |
| 7 | 8.4741 | a[7] | sum[27] |
| 8 | 8.3532 | a[4] | sum[20] |
| 9 | 8.3308 | a[4] | sum[18] |
| 10 | 8.2865 | a[7] | sum[31] |

Summary:

| Metric | Value |
|---|---:|
| Critical path | 9.1405 ns |
| Minimum arrival | 2.9679 ns |
| Average path delay | 6.8211 ns |

The longest paths mostly begin from `a[4]` and end in upper product bits. This suggests that the late path is dominated by the reduction and final carry-propagation region for higher-weight output columns.

### Plain 5:3 Wallace Without BFS

The plain 5:3 version reduces the longest path:

| Rank | Delay (ns) | From | To |
|---:|---:|---|---|
| 1 | 8.9615 | a[6] | sum[28] |
| 2 | 8.8360 | a[6] | sum[25] |
| 3 | 8.8201 | a[6] | sum[29] |
| 4 | 8.8041 | a[6] | sum[24] |
| 5 | 8.6942 | a[6] | sum[30] |
| 6 | 8.6626 | a[6] | sum[26] |
| 7 | 8.5588 | a[6] | sum[23] |
| 8 | 8.5071 | a[6] | sum[22] |
| 9 | 8.5007 | a[6] | sum[27] |
| 10 | 8.4763 | a[6] | sum[21] |

Summary:

| Metric | Value |
|---|---:|
| Critical path | 8.9615 ns |
| Minimum arrival | 3.1161 ns |
| Average path delay | 6.9380 ns |

This confirms the first design idea: using 5:3 compressors can shorten the deepest reduction chain. The critical path moves from `a[4]` in the standard version to `a[6]` in the plain 5:3 version, and the worst endpoint remains in the upper product region.

However, this version also increases physical cost. The post-PnR stdcell area rises from `14392.6` to `15612.5`, and routed wirelength rises from `36080` to `41659`. So the plain 5:3 design buys delay improvement with additional implementation cost.

### BFS Optimized 5:3 Wallace

The BFS-optimized design gives the best observed path delay:

| Rank | Delay (ns) | From | To |
|---:|---:|---|---|
| 1 | 8.8064 | a[5] | sum[29] |
| 2 | 8.6507 | a[5] | sum[31] |
| 3 | 8.6320 | a[5] | sum[30] |
| 4 | 8.6113 | a[5] | sum[26] |
| 5 | 8.5349 | a[5] | sum[27] |
| 6 | 8.4518 | a[5] | sum[24] |
| 7 | 8.4412 | a[5] | sum[25] |
| 8 | 8.4293 | a[5] | sum[28] |
| 9 | 8.2840 | a[5] | sum[23] |
| 10 | 8.2005 | a[5] | sum[22] |

Summary:

| Metric | Value |
|---|---:|
| Critical path | 8.8064 ns |
| Minimum arrival | 3.0019 ns |
| Average path delay | 6.9220 ns |

The optimized design improves on both earlier versions. Compared with the plain 5:3 design, the critical path drops by `0.1551 ns`. Compared with the standard Wallace design, it drops by `0.3341 ns`.

The strongest result is that the BFS version improves delay while also reducing the cost of the plain 5:3 design. It does not beat the standard Wallace design in area, but it makes the 5:3 approach cleaner and more efficient.

## Area and Routing Discussion

| Design | Synthesis Instances | Synthesis Area | Post-PnR Stdcell Area | Core Area | Utilization | Routed Wirelength | Vias |
|---|---:|---:|---:|---:|---:|---:|---:|
| Standard Wallace | 1407 | 13919.6 | 14392.6 | 27629.0 | 0.520922 | 36080 | 11125 |
| Plain 5:3, no BFS | 1575 | 15084.4672 | 15612.5 | 29717.3 | 0.525367 | 41659 | 13439 |
| BFS optimized 5:3 | 1572 | 14822.9664 | 15351.0 | 29480.8 | 0.520711 | 39773 | 13148 |

The standard Wallace design remains the smallest implementation. This is expected because it uses simpler reduction behavior and avoids the extra logic required by larger compressors.

The plain 5:3 version increases synthesis area by about `8.37%` compared with standard Wallace. Its routed wirelength also increases by about `15.46%`. That means the delay improvement is real, but it comes with a larger and more routing-heavy implementation.

The BFS-optimized version improves the plain 5:3 result. It slightly reduces synthesis instance count from `1575` to `1572`, but the more important changes are in physical cost: post-PnR stdcell area drops from `15612.5` to `15351.0`, routed wirelength drops from `41659` to `39773`, and vias drop from `13439` to `13148`. This supports the design intuition that the search-based reduction is avoiding some unnecessary compressor placement.

## Power Comparison

| Design | Internal Power | Switching Power | Leakage Power | Total Power |
|---|---:|---:|---:|---:|
| Standard Wallace | 1.630317e-3 | 2.765684e-3 | 2.803485e-8 | 4.396029e-3 |
| Plain 5:3, no BFS | 8.076471e-4 | 1.255059e-3 | 2.971661e-8 | 2.062736e-3 |
| BFS optimized 5:3 | 7.338804e-4 | 1.081124e-3 | 2.975091e-8 | 1.815034e-3 |

The power result is interesting because the 5:3 designs are larger than the standard Wallace design, but their reported total power is lower. The main reduction comes from internal and switching power, not leakage. This suggests that the changed reduction structure affects switching activity and signal propagation enough to reduce dynamic power, even though the physical implementation has more cells than the standard baseline.

The BFS version is best among the three reported power results. Compared with the plain 5:3 design, it reduces internal power, switching power, and total power. This matches the area/routing observation: the optimized reduction tree does less unnecessary work than the plain 5:3 version.

## Verification and Physical Cleanliness

Before physical implementation, the generated multiplier functionality was checked in Vivado using simulation. This step verified that the generated Verilog produced the expected multiplication result before moving to physical design analysis.

All three designs also completed synthesis with zero unmapped instances and zero synthesis check errors. The reported physical verification metrics show clean final layouts:

| Design | Routing DRC Errors | Magic DRC Errors | LVS Device Differences | LVS Net Differences | LVS Errors |
|---|---:|---:|---:|---:|---:|
| Standard Wallace | 0 | 0 | 0 | 0 | 0 |
| Plain 5:3, no BFS | 0 | 0 | 0 | 0 | 0 |
| BFS optimized 5:3 | 0 | 0 | 0 | 0 | 0 |

This is important for using the folder as project proof. The results are not just generated Verilog comparisons; the designs were taken through physical implementation and finished with clean DRC/LVS metrics.

## Conclusion

The project shows a clear design progression. The standard Wallace multiplier is the most area-efficient baseline, but it has the longest critical path at `9.1405 ns`. Introducing 5:3 compressors reduces the path to `8.9615 ns`, proving that more aggressive compression can shorten the reduction chain. The first 5:3 implementation, however, increases hardware and routing cost.

The BFS-optimized 5:3 design gives the best balance among the optimized variants. It reaches the lowest critical path of `8.8064 ns`, improves delay by about `3.66%` over the standard Wallace multiplier, and reduces area, routed wirelength, vias, and total power compared with the plain 5:3 version.

The final result is not that 5:3 compression is automatically better in every metric. The better conclusion is more careful: 5:3 compressors can reduce delay, but their placement matters. A search-based reduction strategy helps preserve the timing benefit while reducing unnecessary hardware cost.
