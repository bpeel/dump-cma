#!/usr/bin/python3

from collections import namedtuple
import re
import curses
import time


CMA_POOL_SIZE = 316 * 1024 * 1024
# Y position of where to draw the map
MAP_Y = 1
# Number of characters either side of the map
MAP_PADDING = 3
# Height of the map in characters
MAP_HEIGHT = 8
# Y position of where to print the total size of allocations
TOTAL_Y = MAP_Y + MAP_HEIGHT + 1
# Y position of where to print the list of allocations
BUFFER_LIST_Y = TOTAL_Y + 2


Buffer = namedtuple('Buffer', ['address', 'size'])


def get_buffers():
    regex = re.compile(r'^gpu vc4-drm.* '
                       r'P=(?P<paddr>[0-9a-f]+).* '
                       r'L=(?P<size>[0-9a-f]+)')

    with open("/sys/kernel/debug/dma-api/dump", 'rt') as f:
        for line in f:
            md = regex.match(line)
            if md is None:
                continue

            yield Buffer(int(md.group('paddr'), 16),
                         int(md.group('size'), 16))


def draw_map_range(stdscr, start, size, fill):
    map_width = curses.COLS - MAP_PADDING * 2
    start_pos = start * map_width // CMA_POOL_SIZE
    end_pos = ((start + size) * map_width + CMA_POOL_SIZE - 1) // CMA_POOL_SIZE

    line = ("#" if fill else " ") * (end_pos - start_pos)

    for i in range(MAP_HEIGHT):
        stdscr.addstr(i + 1, MAP_PADDING + start_pos, line)


def draw_map(stdscr, buffers):
    if len(buffers) <= 0:
        draw_map_range(0, CMA_POOL_SIZE, false)
        return

    start_address = buffers[0].address
    last_address = start_address

    for buf in buffers:
        if buf.address > last_address:
            draw_map_range(stdscr,
                           last_address - start_address,
                           buf.address - last_address,
                           False)
        draw_map_range(stdscr, buf.address - start_address, buf.size, True)

        last_address = buf.address + buf.size

    if last_address < CMA_POOL_SIZE:
        draw_map_range(stdscr,
                       last_address,
                       CMA_POOL_SIZE - last_address,
                       False)


def pretty_size(size):
    if size < 1024:
        return str(size)
    if size < 1024 * 1024:
        return "{:.2f}kb".format(size / 1024)
    return "{:.2f}mb".format(size / (1024 * 1024))


def print_total(stdscr, buffers):
    total_size = sum(b.size for b in buffers)
    stdscr.addstr(TOTAL_Y,
                  0,
                  "{} / {}".format(pretty_size(total_size),
                                   pretty_size(CMA_POOL_SIZE)))
    stdscr.clrtoeol()


def list_buffers(stdscr, buffers):
    y_pos = BUFFER_LIST_Y

    for i, buf in enumerate(buffers):
        if i + y_pos >= curses.LINES:
            break

        stdscr.move(i + y_pos, 0)
        stdscr.clrtoeol()

        line = "0x{:08x} {}".format(buf.address, pretty_size(buf.size))
        stdscr.addstr(line)

    # Clear the rest of the terminal after the list
    if y_pos + len(buffers) < curses.LINES:
        stdscr.move(y_pos + len(buffers), 0)
        stdscr.clrtobot()


def main(stdscr):
    while True:
        buffers = list(get_buffers())
        buffers.sort(key = lambda b: b.address)

        draw_map(stdscr, buffers)
        print_total(stdscr, buffers)
        list_buffers(stdscr, buffers)
        stdscr.refresh()
        time.sleep(1)


if __name__ == "__main__":
    curses.wrapper(main)
