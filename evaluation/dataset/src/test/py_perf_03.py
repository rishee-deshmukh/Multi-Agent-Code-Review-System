def render_csv(header, rows):
    out = ",".join(header) + "\n"
    for row in rows:
        out = out + ",".join(str(cell) for cell in row) + "\n"  # @label string_concat_loop low
    return out


def column_widths(header, rows):
    widths = [len(h) for h in header]
    for row in rows:
        widths = [max(w, len(str(c))) for w, c in zip(widths, row)]
    return widths
