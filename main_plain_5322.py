from wallace_generator import (
    reduce_wallace_normal,
    verify_result,
    write_pdf,
    write_report,
    write_testbench,
    write_verilog,
)


N = 32
RANDOM_TESTS = 500


if __name__ == "__main__":
    result = reduce_wallace_normal(width=N)
    verify_result(result, width=N, random_tests=RANDOM_TESTS)
    write_report(
        result,
        f"matrix_phases_plain_5322_{N}bit.txt",
        width=N,
        title="plain_greedy_5to3_3to2_2to2",
    )
    write_pdf(result, f"matrix_phases_plain_5322_{N}bit.pdf", width=N)
    write_verilog(result, f"wallace{N}_plain_5322.v", width=N, variant="normal")
    write_testbench(result, f"tb_wallace{N}_plain_5322.v", width=N, variant="normal")

    max_height = max((len(bits) for bits in result.columns.values()), default=0)
    c53 = sum(1 for i in result.instances if i.kind == "c53")
    c32 = sum(1 for i in result.instances if i.kind == "c32")
    c22 = sum(1 for i in result.instances if i.kind == "c22")
    print(
        f"plain_5322_{N}bit: stages={len(result.stages)}, instances={len(result.instances)}, "
        f"c53={c53}, c32={c32}, c22={c22}, final_max_height={max_height}, final_rows={len(result.rows)}"
    )
