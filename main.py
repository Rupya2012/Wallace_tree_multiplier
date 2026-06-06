from wallace_generator import generate_compare


N = 32
RANDOM_TESTS = 500


if __name__ == "__main__":
    optimized, normal = generate_compare(width=N, random_tests=RANDOM_TESTS)

    def summarize(tag: str, result) -> None:
        max_height = max((len(bits) for bits in result.columns.values()), default=0)
        c53 = sum(1 for i in result.instances if i.kind == "c53")
        c32 = sum(1 for i in result.instances if i.kind == "c32")
        c22 = sum(1 for i in result.instances if i.kind == "c22")
        print(
            f"{tag}_{N}bit: stages={len(result.stages)}, instances={len(result.instances)}, "
            f"c53={c53}, c32={c32}, c22={c22}, final_max_height={max_height}, final_rows={len(result.rows)}"
        )

    summarize("optimized", optimized)
    summarize("normal", normal)
