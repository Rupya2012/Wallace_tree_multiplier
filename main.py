from standard_wallace_generator import generate_all as generate_standard
from wallace_generator import (
    generate_all as generate_optimized,
    reduce_wallace_normal,
    verify_result,
    write_pdf,
    write_report,
    write_verilog,
)


N = 16
RANDOM_TESTS = 500


if __name__ == "__main__":
    standard = generate_standard(width=N, random_tests=RANDOM_TESTS)
    plain = reduce_wallace_normal(width=N)
    verify_result(plain, width=N, random_tests=RANDOM_TESTS)
    write_report(
        plain,
        f"matrix_phases_plain_5322_{N}bit.txt",
        width=N,
        title="plain_greedy_5to3_3to2_2to2",
    )
    write_pdf(plain, f"matrix_phases_plain_5322_{N}bit.pdf", width=N)
    write_verilog(plain, f"wallace{N}_plain_5322.v", width=N, variant="normal")
    optimized = generate_optimized(width=N, random_tests=RANDOM_TESTS)

    def summarize(tag: str, result) -> None:
        max_height = max((len(bits) for bits in result.columns.values()), default=0)
        c53 = sum(1 for i in result.instances if i.kind == "c53")
        c32 = sum(1 for i in result.instances if i.kind == "c32")
        c22 = sum(1 for i in result.instances if i.kind == "c22")
        final_rows = len(result.rows) if hasattr(result, "rows") else 2
        print(
            f"{tag}_{N}bit: stages={len(result.stages)}, instances={len(result.instances)}, "
            f"c53={c53}, c32={c32}, c22={c22}, final_max_height={max_height}, final_rows={final_rows}"
        )

    summarize("standard", standard)
    summarize("plain_5322", plain)
    summarize("optimized", optimized)
