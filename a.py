from typing import Sequence
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

VerticalBox = tuple[int, int, int]  # (col_no, start_row_no, number_of_boxes)


def greedy_vertical_boxes_from_matrix(
    m: Sequence[Sequence[int]],
    index_base: int = 1,
    min_size: int = 1,
    max_size: int = 4,
    extralist: Sequence[VerticalBox] = (),
) -> list[VerticalBox]:
    """Return vertical box tuples per column using greedy sizes in [max_size..min_size].

    Output tuples are compatible with matrix_to_tick_cross_png:
    (col_no, start_row_no, number_of_boxes)

    Any tuple in ``extralist`` is forced as-is and won't be split.
    """
    if not m or not m[0]:
        raise ValueError("Input matrix must be a non-empty list of non-empty lists.")
    if min_size < 1 or max_size < 1:
        raise ValueError("min_size and max_size must be positive integers.")
    if min_size > max_size:
        raise ValueError("min_size cannot be greater than max_size.")

    rows = len(m)
    cols = len(m[0])
    if any(len(row) != cols for row in m):
        raise ValueError("All rows must have the same number of columns.")

    for row in m:
        for value in row:
            if value not in (0, 1, False, True):
                raise ValueError("Matrix values must be only 0 or 1.")

    forced_by_col: dict[int, list[tuple[int, int, int]]] = {}
    for col_no, start_row_no, box_count in extralist:
        if box_count < 1:
            raise ValueError("extralist box size must be at least 1.")
        col_idx = col_no - index_base
        row_idx = start_row_no - index_base
        if col_idx < 0 or col_idx >= cols:
            raise ValueError(f"extralist col_no out of range: {col_no}")
        if row_idx < 0 or row_idx >= rows:
            raise ValueError(f"extralist start_row_no out of range: {start_row_no}")
        if row_idx + box_count > rows:
            raise ValueError(f"extralist box exceeds rows: {(col_no, start_row_no, box_count)}")
        for rr in range(row_idx, row_idx + box_count):
            if int(m[rr][col_idx]) != 1:
                raise ValueError(
                    f"extralist box must lie on 1-cells only: {(col_no, start_row_no, box_count)}"
                )
        forced_by_col.setdefault(col_idx, []).append((row_idx, row_idx + box_count, box_count))

    for col_idx, intervals in forced_by_col.items():
        intervals.sort(key=lambda x: x[0])
        for i in range(1, len(intervals)):
            if intervals[i][0] < intervals[i - 1][1]:
                raise ValueError(
                    f"extralist boxes overlap in column {col_idx + index_base}."
                )

    boxes: list[VerticalBox] = []

    def emit_segment(col_idx: int, seg_start: int, seg_len: int) -> None:
        run_remaining = seg_len
        run_start = seg_start
        while run_remaining > 0:
            if run_remaining < min_size:
                while run_remaining > 0:
                    boxes.append((col_idx + index_base, run_start + index_base, 1))
                    run_start += 1
                    run_remaining -= 1
                break
            if run_remaining <= max_size:
                chosen_size = run_remaining
            else:
                chosen_size = max_size
            boxes.append((col_idx + index_base, run_start + index_base, chosen_size))
            run_start += chosen_size
            run_remaining -= chosen_size

    for c in range(cols):
        r = 0
        forced_intervals = forced_by_col.get(c, [])
        while r < rows:
            if int(m[r][c]) != 1:
                r += 1
                continue

            start = r
            while r < rows and int(m[r][c]) == 1:
                r += 1

            run_forced = [interval for interval in forced_intervals if start <= interval[0] and interval[1] <= r]
            cursor = start
            for forced_start, forced_end, forced_count in run_forced:
                if forced_start > cursor:
                    emit_segment(c, cursor, forced_start - cursor)
                boxes.append((c + index_base, forced_start + index_base, forced_count))
                cursor = forced_end
            if cursor < r:
                emit_segment(c, cursor, r - cursor)
    
    return boxes


def output_values_for_single_tick_rows(m: Sequence[Sequence[int]]) -> list[int]:
    """Return per-column counts of 1s (kept name for backward compatibility)."""
    if not m or not m[0]:
        raise ValueError("Input matrix must be a non-empty list of non-empty lists.")

    rows = len(m)
    cols = len(m[0])
    if any(len(row) != cols for row in m):
        raise ValueError("All rows must have the same number of columns.")

    output_values = [0] * cols
    for r in range(rows):
        for c in range(cols):
            value = m[r][c]
            if value not in (0, 1, False, True):
                raise ValueError("Matrix values must be only 0 or 1.")
            output_values[c] += int(value)
    output_values = [0 if count != 1 else 1 for count in output_values]
    for c in range(cols-2, -1, -1):
        output_values[c] = min(output_values[c], output_values[c+1])
    return output_values


def build_compact_matrix_from_boxes(
    boxes: Sequence[VerticalBox],
    total_cols: int,
    index_base: int = 1,
    return_tick_sources: bool = False,
    n3_size: int | None = None,
) -> list[list[int]] | tuple[list[list[int]], list[list[VerticalBox | None]]]:
    """Build a minimum-height, top-aligned matrix from box tuples.

    Rules:
    - box_count == 1        -> pass one bit in its column
    - box_count in (2, 3)   -> exact 2:2/3:2 output in current and next column
    - box_count == n3_size  -> exact N:3 output in current, next, and next+1 column

    Columns are LSB-first hardware columns. Carries move to higher columns.

    When return_tick_sources=True, also returns a parallel list-of-lists where
    each tick cell contains its source (col_no, start_row_no, number_of_boxes),
    and cross cells contain None.
    """
    if total_cols <= 0:
        raise ValueError("total_cols must be positive.")
    if n3_size is not None and n3_size not in (4, 5, 6, 7):
        raise ValueError("n3_size must be one of 4, 5, 6, 7 when provided.")

    for col_no, _start_row_no, box_count in boxes:
        if box_count < 1 or box_count > 7:
            raise ValueError("number_of_boxes must be between 1 and 7.")
        col_idx = col_no - index_base
        if col_idx < 0 or col_idx >= total_cols:
            raise ValueError(f"col_no out of range: {col_no}")

    col_tick_sources: list[list[VerticalBox]] = [[] for _ in range(total_cols)]
    for col_no, start_row_no, box_count in boxes:
        col_idx = col_no - index_base
        src = (col_no, start_row_no, box_count)
        col_tick_sources[col_idx].append(src)
        if box_count in (2, 3):
            if col_idx + 1 < total_cols:
                col_tick_sources[col_idx + 1].append(src)
        elif n3_size is not None and box_count == n3_size:
            if col_idx + 1 < total_cols:
                col_tick_sources[col_idx + 1].append(src)
            if col_idx + 2 < total_cols:
                col_tick_sources[col_idx + 2].append(src)
        elif box_count not in (1,):
            raise ValueError(
                f"box_count {box_count} is not valid for this reduction mode; "
                "use 1, 2, 3, or the selected n3_size."
            )

    row_count = max((len(col_sources) for col_sources in col_tick_sources), default=0)
    matrix = [[0 for _ in range(total_cols)] for _ in range(row_count)]
    tick_sources: list[list[VerticalBox | None]] = [[None for _ in range(total_cols)] for _ in range(row_count)]
    for c, col_sources in enumerate(col_tick_sources):
        for r, src in enumerate(col_sources):
            matrix[r][c] = 1
            tick_sources[r][c] = src

    if return_tick_sources:
        return matrix, tick_sources
    return matrix


def _draw_tick(draw: ImageDraw.ImageDraw, x0: float, y0: float, cell_size: float, color: str) -> None:
    """Draw a scalable tick mark independent of font support."""
    p1 = (x0 + 0.22 * cell_size, y0 + 0.56 * cell_size)
    p2 = (x0 + 0.42 * cell_size, y0 + 0.76 * cell_size)
    p3 = (x0 + 0.78 * cell_size, y0 + 0.30 * cell_size)
    draw.line([p1, p2], fill=color, width=max(2, int(cell_size * 0.08)))
    draw.line([p2, p3], fill=color, width=max(2, int(cell_size * 0.08)))


def _draw_cross(draw: ImageDraw.ImageDraw, x0: float, y0: float, cell_size: float, color: str) -> None:
    """Draw a scalable cross mark independent of font support."""
    a = (x0 + 0.25 * cell_size, y0 + 0.25 * cell_size)
    b = (x0 + 0.75 * cell_size, y0 + 0.75 * cell_size)
    c = (x0 + 0.75 * cell_size, y0 + 0.25 * cell_size)
    d = (x0 + 0.25 * cell_size, y0 + 0.75 * cell_size)
    stroke = max(2, int(cell_size * 0.08))
    draw.line([a, b], fill=color, width=stroke)
    draw.line([c, d], fill=color, width=stroke)


def matrix_to_tick_cross_png(
    m: Sequence[Sequence[int]],
    output_path: str = "matrix.png",
    vertical_boxes: Sequence[VerticalBox] = (),
    output_values: Sequence[int] | None = None,
    phase_i: int | str = 1,
    cell_size: int = 56,
    padding: int = 20,
    label_margin: int = 40,
    index_base: int = 1,
) -> str:
    """Render a 0/1 matrix to a PNG grid with labels, optional boxes, and output values.

    output_values must be length == cols and is rendered as a bottom row.
    """
    if not m or not m[0]:
        raise ValueError("Input matrix must be a non-empty list of non-empty lists.")

    rows = len(m)
    cols = len(m[0])
    if any(len(row) != cols for row in m):
        raise ValueError("All rows must have the same number of columns.")

    for row in m:
        for value in row:
            if value not in (0, 1, False, True):
                raise ValueError("Matrix values must be only 0 or 1.")

    if output_values is None:
        output_values = [0] * cols
    output_count = len(output_values)
    if output_count != cols:
        raise ValueError("output_values length must match number of matrix columns.")
    for value in output_values:
        if not isinstance(value, int) or value < 0:
            raise ValueError("output_values must contain non-negative integers.")

    for col_no, start_row_no, box_count in vertical_boxes:
        if box_count < 1 or box_count > 7:
            raise ValueError("number_of_boxes must be between 1 and 7.")
        col_idx = col_no - index_base
        row_idx = start_row_no - index_base
        if col_idx < 0 or col_idx >= cols:
            raise ValueError(f"col_no out of range: {col_no}")
        if row_idx < 0 or row_idx >= rows:
            raise ValueError(f"start_row_no out of range: {start_row_no}")
        if row_idx + box_count > rows:
            raise ValueError(
                f"Vertical box (col={col_no}, start_row={start_row_no}, count={box_count}) exceeds matrix rows."
            )

    title_height = label_margin
    output_gap = max(10, int(cell_size * 0.35))
    grid_x0 = padding + label_margin
    grid_y0 = padding + title_height + label_margin
    output_x0 = grid_x0
    output_y0 = grid_y0 + rows * cell_size + output_gap
    width = max(grid_x0 + cols * cell_size + padding, output_x0 + output_count * cell_size + padding)
    height = output_y0 + cell_size + padding

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    title = f"Calculation - Phase {phase_i}"
    title_bbox = draw.textbbox((0, 0), title, font=font)
    title_w = title_bbox[2] - title_bbox[0]
    title_h = title_bbox[3] - title_bbox[1]
    draw.text(((width - title_w) / 2, padding + (title_height - title_h) / 2), title, fill="#111111", font=font)

    green_cols = {i for i, value in enumerate(output_values[:cols]) if int(value) == 1}

    # Draw cells and symbols.
    for r in range(rows):
        for c in range(cols):
            x0 = grid_x0 + c * cell_size
            y0 = grid_y0 + r * cell_size
            x1 = x0 + cell_size
            y1 = y0 + cell_size
            if c in green_cols:
                draw.rectangle([x0, y0, x1, y1], fill="#d2f4d2")
            draw.rectangle([x0, y0, x1, y1], outline="#444444", width=2)

            if int(m[r][c]) == 1:
                _draw_tick(draw, x0, y0, cell_size, "#1a7f37")
            else:
                _draw_cross(draw, x0, y0, cell_size, "#cf222e")

    # Column labels.

    for c in range(cols):
        label = str(c + index_base)
        x = grid_x0 + c * cell_size + cell_size / 2
        y = grid_y0 - (label_margin / 2)
        bbox = draw.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((x - tw / 2, y - th / 2), label, fill="#111111", font=font)

    # Row labels.
    for r in range(rows):
        label = str(r + index_base)
        x = grid_x0 - (label_margin / 2)
        y = grid_y0 + r * cell_size + cell_size / 2
        bbox = draw.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((x - tw / 2, y - th / 2), label, fill="#111111", font=font)

    # Output block.
    output_label = "Output"
    out_bbox = draw.textbbox((0, 0), output_label, font=font)
    out_w = out_bbox[2] - out_bbox[0]
    out_h = out_bbox[3] - out_bbox[1]
    out_label_x = grid_x0 - (label_margin / 2)
    out_label_y = output_y0 + cell_size / 2
    draw.text((out_label_x - out_w / 2, out_label_y - out_h / 2), output_label, fill="#111111", font=font)

    for c in range(output_count):
        x0 = output_x0 + c * cell_size
        y0 = output_y0
        x1 = x0 + cell_size
        y1 = y0 + cell_size
        draw.rectangle([x0, y0, x1, y1], outline="#444444", width=2)

        if int(output_values[c]) == 1:
            _draw_tick(draw, x0, y0, cell_size, "#1a7f37")

    # Optional vertical highlight boxes.
    for col_no, start_row_no, box_count in vertical_boxes:
        if box_count < 1 or box_count > 7:
            raise ValueError("number_of_boxes must be between 1 and 7.")
        col_idx = col_no - index_base
        row_idx = start_row_no - index_base
        inset = max(4, int(cell_size * 0.12))
        x0 = grid_x0 + col_idx * cell_size + inset
        y0 = grid_y0 + row_idx * cell_size + inset
        x1 = grid_x0 + (col_idx + 1) * cell_size - inset
        y1 = grid_y0 + (row_idx + box_count) * cell_size - inset
        draw.rectangle([x0, y0, x1, y1], outline="#0969da", width=max(2, int(cell_size * 0.06)))

    image.save(output_path, format="PNG")
    return output_path

def init_matrix(N, M):
    matrix = [[0 for _ in range(M)] for _ in range(N)]
    for i in range(N):
        for j in range(N):
            matrix[N-1-i][i+j] = 1
    return matrix


def export_pdf_and_delete_images(
    image_paths: list[str],
    pdf_path: str = "matrix_phases.pdf",
    phase_box_counts: Sequence[dict[int, int]] | None = None,
) -> None:
    if not image_paths:
        return

    images = [Image.open(path).convert("RGB") for path in image_paths]
    if phase_box_counts is not None:
        summary = Image.new("RGB", images[0].size, "white")
        draw = ImageDraw.Draw(summary)
        font = ImageFont.load_default()

        x = 40
        y = 30
        line_h = 24
        draw.text((x, y), "Box Usage Summary (sizes 7, 6, 5, 4, 3, 2)", fill="#111111", font=font)
        y += line_h * 2

        sizes = [7, 6, 5, 4, 3, 2]
        total = {size: 0 for size in sizes}
        for phase_i, counts in enumerate(phase_box_counts):
            parts = []
            for size in sizes:
                count = int(counts.get(size, 0))
                total[size] += count
                parts.append(f"{size}-box={count}")
            line = f"Phase {phase_i}: " + ", ".join(parts)
            draw.text((x, y), line, fill="#111111", font=font)
            y += line_h

        y += line_h
        total_line = "Total: " + ", ".join(f"{size}-box={total[size]}" for size in sizes)
        draw.text((x, y), total_line, fill="#111111", font=font)
        images.append(summary)

    images[0].save(pdf_path, save_all=True, append_images=images[1:])

    for image in images:
        image.close()

    for path in image_paths:
        Path(path).unlink(missing_ok=True)


