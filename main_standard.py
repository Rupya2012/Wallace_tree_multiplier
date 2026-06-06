from standard_wallace_generator import generate_all


N = 16
RANDOM_TESTS = 500


if __name__ == "__main__":
    result = generate_all(width=N, random_tests=RANDOM_TESTS)
    max_height = max((len(bits) for bits in result.columns.values()), default=0)
    c32 = sum(1 for i in result.instances if i.kind == "c32")
    c22 = sum(1 for i in result.instances if i.kind == "c22")
    print(
        f"standard_{N}bit: stages={len(result.stages)}, instances={len(result.instances)}, "
        f"c32={c32}, c22={c22}, final_max_height={max_height}"
    )
