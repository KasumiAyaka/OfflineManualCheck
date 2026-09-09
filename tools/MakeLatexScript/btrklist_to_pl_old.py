import sys
from pathlib import Path

# ECC6 プロジェクト固有の定数 (\PL{ECC_NUM}{...} の第1引数)
ECC_NUM = 6

# \EventList{} に入れる Event の最大数。これを超えた分は \PL{} の外の \Events{} に出力する。
EVENT_LIST_LIMIT = 34


def parse_blocks(lines):
    """btrklist.txt を PL 単位のブロックに分割する。

    1トークンの行 -> 新しい PL の開始。
    4トークンの行 -> (area, eventid, btrackid, btrackid2)。
    """
    blocks = []
    cur_pl = None
    cur_rows = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) == 1:
            if cur_pl is not None:
                blocks.append((cur_pl, cur_rows))
            cur_pl = int(parts[0])
            cur_rows = []
        elif len(parts) == 4:
            area, eventid, btrackid, btrackid2 = (int(p) for p in parts)
            cur_rows.append((area, eventid, btrackid, btrackid2))
        else:
            raise ValueError("想定外の行フォーマット: {!r}".format(raw))
    if cur_pl is not None:
        blocks.append((cur_pl, cur_rows))
    return blocks


def event_value(eventid, btrackid, btrackid2):
    """1行分の (eventid, btrackid, btrackid2) から (出力する値, ルール1を満たすか) を決める。

    1. btrackid > 0 かつ btrackid2 > 0 : eventid を出力 (ルール1: 満たす)
    2. btrackid2 == -1                 : btrackid を出力
    3. btrackid2 == 0                  : eventid を出力
    """
    if btrackid > 0 and btrackid2 > 0:
        return eventid, True
    if btrackid2 == -1:
        return btrackid, False
    if btrackid2 == 0:
        return eventid, False
    raise ValueError(
        "想定外の (btrackid, btrackid2) の組み合わせ: ({}, {})".format(btrackid, btrackid2)
    )


def format_event_list(name, items, indent):
    """\\<name>{ ... } を indent タブ分の深さで出力する (中の \\Event は indent+1 タブ)。"""
    tab = "\t" * indent
    inner = "\t" * (indent + 1)
    out = ["{}\\{}{{".format(tab, name)]
    for value, rule1, area in items:
        flag = "o" if rule1 else " "
        out.append("{}\\Event{{{}}}{{{}}}{{{}}}".format(inner, value, flag, area))
    out.append(inner)
    out.append("{}}}".format(tab))
    return out


def format_block(pl, rows, const=ECC_NUM):
    areas = sorted({area for area, _eventid, _btrackid, _btrackid2 in rows})
    events = [
        event_value(eventid, btrackid, btrackid2) + (area,)
        for area, eventid, btrackid, btrackid2 in rows
    ]

    first32 = events[:EVENT_LIST_LIMIT]
    rest = events[EVENT_LIST_LIMIT:]

    out = []
    out.append("\\PL{{{}}}{{{:03d}}}{{".format(const, pl))
    out.append("\t\\AreaList{")
    for area in areas:
        out.append("\t\t\\Area{{{}}}".format(area))
    out.append("\t}\t")
    out.append("}{")
    out.extend(format_event_list("EventList", first32, indent=1))
    out.append("}")

    if rest:
        out.extend(format_event_list("Events", rest, indent=0))

    return out


def convert(input_path, output_path):
    with input_path.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    blocks = parse_blocks(lines)

    block_texts = ["\n".join(format_block(pl, rows)) for pl, rows in blocks]
    with output_path.open("w", encoding="utf-8", newline="\r\n") as f:
        f.write("\n".join(block_texts))

    return len(blocks)


def main():
    if len(sys.argv) >= 2:
        input_path = Path(sys.argv[1])
    else:
        input_path = Path(__file__).resolve().parent.parent / "btrklist.txt"

    if len(sys.argv) >= 3:
        output_path = Path(sys.argv[2])
    else:
        output_path = input_path.with_name(input_path.stem + "_conv.txt")

    n = convert(input_path, output_path)
    print("input : {}".format(input_path))
    print("output: {}".format(output_path))
    print("{} 個の PL ブロックを出力しました。".format(n))


if __name__ == "__main__":
    main()
