# Area-Aware 16-bit Wallace Multiplier Using 5:3 Compressors

## Overview

This project studies a 16-bit unsigned multiplier where the partial products are reduced using Wallace-style compression before a final parallel prefix adder. The final adder used in the project is a Kogge-Stone adder; the work in this folder focuses on the reduction network that produces the final two rows.

Three reduction styles are compared:

| Design | Compressor strategy | Reduction stages | Total compressors | 5:3 | 3:2 | 2:2 |
|---|---:|---:|---:|---:|---:|---:|
| Standard Wallace | 3:2 and 2:2 only | 6 | 254 | 0 | 196 | 58 |
| Plain 5:3 Wallace | Greedy 5:3, then 3:2, then 2:2 | 5 | 159 | 70 | 56 | 33 |
| BFS optimized 5:3 Wallace | Mostly 5:3, with only required 3:2 and 2:2 placements | 5 | 126 | 81 | 36 | 9 |

The optimized design reaches the same 5-stage reduction depth as the unrestricted plain 5:3 flow, while using fewer hardware elements. Compared with the plain 5:3 Wallace reduction, the BFS-optimized design removes 33 compressors. Compared with the standard Wallace reduction, it removes 128 compressors and also reduces the number of reduction stages from 6 to 5.

## Compressor Structure

Leave space here for the exact 5:3 compressor structure used in the implementation.

```
// Add 5:3 compressor logic / diagram / gate-level structure here.
```

## Design Progression

The project began with a standard Wallace tree. In that version, the reduction network used only 3:2 compressors and 2:2 compressors. This gave a clean baseline and made it easy to verify the partial-product reduction process.

The next step was to introduce 5:3 compressors. A 5:3 compressor can reduce more bits in a column at once, so the expectation was that it would reduce the number of reduction phases and improve the critical path through the reduction tree. The first plain 5:3 version used a greedy policy: whenever a column had enough bits, use 5:3 first, then use 3:2, then use 2:2. This reached 5 stages for the 16-bit multiplier, which established the minimum stage target for this project.

After that, the main concern became hardware cost. The plain greedy design used fewer stages, but it still inserted many smaller compressors. The question became: can the design still reach the 5-stage target while using fewer 3:2 and 2:2 compressors?

That led to the BFS optimized version. Instead of automatically using every possible 3:2 and 2:2 compressor, the optimizer searches for only the required placements. The goal is to preserve the 5-stage reduction depth while reducing hardware count, area, and power.

## BFS Optimization Method

The BFS optimizer models the multiplier as a column-height reduction problem. Each stage transforms one column-height profile into a new profile. A 5:3 compressor consumes 5 bits in one column and produces outputs in the same column, the next column, and the column after that. A 3:2 compressor consumes 3 bits and produces outputs in the same and next column. A 2:2 compressor consumes 2 bits and produces outputs in the same and next column.

The search is constrained by the target number of stages. For the 16-bit design, the plain 5:3 Wallace tree showed that 5 stages are achievable, so BFS is configured to find a valid 5-stage schedule. The optimizer gives priority to fewer small compressors, especially fewer 2:2 compressors, because these extra elements increase area and switching activity.

The resulting optimized placement uses more 5:3 compressors than the plain 5:3 design, but far fewer 3:2 and 2:2 compressors:

| Comparison | Total compressor saving | 3:2 saving | 2:2 saving |
|---|---:|---:|---:|
| Optimized vs Plain 5:3 | 33 fewer | 20 fewer | 24 fewer |
| Optimized vs Standard | 128 fewer | 160 fewer | 49 fewer |

## Reduction Outputs

The following generated files document the three final 16-bit reduction structures:

| Design | Phase report | Verilog |
|---|---|---|
| Standard Wallace | `matrix_phases_standard_16bit.txt/pdf` | `wallace16_standard.v` |
| Plain 5:3 Wallace | `matrix_phases_plain_5322_16bit.txt/pdf` | `wallace16_plain_5322.v` |
| BFS optimized 5:3 Wallace | `matrix_phases_n3_5_16bit.txt/pdf` | `wallace16_n3_5.v` |

## Timing and Critical Path Results

Do not include slack or clock-only metrics here. Fill this table using the final synthesis/timing values from the notebooks or Vivado reports.

| Design | Critical path | Data path delay | Logic delay | Routing delay | Logic levels |
|---|---:|---:|---:|---:|---:|
| Standard Wallace + Kogge-Stone |  |  |  |  |  |
| Plain 5:3 Wallace + Kogge-Stone |  |  |  |  |  |
| BFS optimized 5:3 Wallace + Kogge-Stone |  |  |  |  |  |

## Area and Power Results

Fill this table with the final area and power results from the notebook/Vivado output. The key comparison should focus on area and power, not slack.

| Design | LUTs / cells | Registers | Carry resources | Dynamic power | Static power | Total power |
|---|---:|---:|---:|---:|---:|---:|
| Standard Wallace + Kogge-Stone |  |  |  |  |  |  |
| Plain 5:3 Wallace + Kogge-Stone |  |  |  |  |  |  |
| BFS optimized 5:3 Wallace + Kogge-Stone |  |  |  |  |  |  |

## Conclusion

The standard Wallace tree is a useful baseline, but it needs 6 reduction stages and 254 compressors for the 16-bit case. Introducing 5:3 compressors reduces the reduction depth to 5 stages and cuts the compressor count to 159. The BFS optimized design keeps the same 5-stage target while reducing the compressor count further to 126.

This is the main result of the project: the optimized 5:3 Wallace tree reaches the same minimum observed reduction-stage count as the unrestricted greedy 5:3 design, but with much lower compressor usage. This should translate into lower area and lower switching power, while still preserving the shorter reduction depth before the Kogge-Stone final adder.
