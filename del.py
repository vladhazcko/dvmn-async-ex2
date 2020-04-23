import asyncio
import curses
import time
import random
from itertools import cycle

SPACE_KEY_CODE = 32
LEFT_KEY_CODE = 260
RIGHT_KEY_CODE = 261
UP_KEY_CODE = 259
DOWN_KEY_CODE = 258


def draw(canvas):
    curses.curs_set(False)
    canvas.border()
    canvas.nodelay(True)
    y_max, x_max = canvas.getmaxyx()
    y_min, x_min = canvas.getbegyx()
    ship_height, ship_width = get_frame_size(rocket_frames[0])
    fire_height = fire_width = 1
    star_height = star_width = 1
    border = 1

    coroutines = [fire(canvas, y_max - border - fire_height - ship_height, x_max // 2),
                  animate_spaceship(canvas, y_max - ship_height - border, (x_max - ship_width) // 2)]

    stars_count = 50
    for _ in range(stars_count):
        row = random.randint(y_min + border + star_height, y_max - border - star_height)
        column = random.randint(x_min + border + star_width, x_max - border - star_width)
        symbol = random.choice(['*', '+', '.', ':'])
        coroutines.append(blink(canvas, row, column, symbol))

    while True:
        for coroutine in coroutines.copy():
            try:
                coroutine.send(None)
            except StopIteration:
                coroutines.remove(coroutine)
        canvas.refresh()
        time.sleep(0.1)


async def blink(canvas, row, column, symbol='*'):
    """Display animation of star"""
    while True:
        delay = random.randint(0, 30)
        for _ in range(delay):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol, curses.A_DIM)
        for _ in range(20):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        for _ in range(3):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        for _ in range(5):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        for _ in range(3):
            await asyncio.sleep(0)


async def fire(canvas, start_row, start_column, rows_speed=-0.3, columns_speed=0):
    """Display animation of gun shot. Direction and speed can be specified."""

    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), '*')
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), 'O')
    await asyncio.sleep(0)
    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


async def animate_spaceship(canvas, row, column):
    height, width = get_frame_size(rocket_frames[0])
    delta_y, delta_x = canvas.getmaxyx()

    y_min, x_min = canvas.getbegyx()
    y_max, x_max = y_min + delta_y - height - 1, x_min + delta_x - width - 1

    for rocket_frame in cycle(rocket_frames):
        draw_frame(canvas, row, column, rocket_frame)
        await asyncio.sleep(0)

        draw_frame(canvas, row, column, rocket_frame, negative=True)

        dy, dx, space = read_controls(canvas)
        row = min(row + dy, y_max) if dy > 0 else max(y_min + 1, row + dy)
        column = min(column + dx, x_max) if dx > 0 else max(x_min + 1, column + dx)


def draw_frame(canvas, start_row, start_column, text, negative=False):
    """Draw multiline text fragment on canvas. Erase text instead of drawing if negative=True is specified."""

    rows_number, columns_number = canvas.getmaxyx()

    for row, line in enumerate(text.splitlines(), round(start_row)):
        if row < 0:
            continue

        if row >= rows_number:
            break

        for column, symbol in enumerate(line, round(start_column)):
            if column < 0:
                continue

            if column >= columns_number:
                break

            if symbol == ' ':
                continue

            # Check that current position it is not in a lower right corner of the window
            # Curses will raise exception in that case. Don`t ask why…
            # https://docs.python.org/3/library/curses.html#curses.window.addch
            if row == rows_number - 1 and column == columns_number - 1:
                continue

            symbol = symbol if not negative else ' '
            canvas.addch(row, column, symbol)


def read_controls(canvas):
    """Read keys pressed and returns tuple witl controls state."""

    rows_direction = columns_direction = 0
    space_pressed = False
    speed = 1

    while True:
        pressed_key_code = canvas.getch()

        if pressed_key_code == -1:
            # https://docs.python.org/3/library/curses.html#curses.window.getch
            break

        if pressed_key_code == UP_KEY_CODE:
            rows_direction = -speed

        if pressed_key_code == DOWN_KEY_CODE:
            rows_direction = speed

        if pressed_key_code == RIGHT_KEY_CODE:
            columns_direction = speed

        if pressed_key_code == LEFT_KEY_CODE:
            columns_direction = -speed

        if pressed_key_code == SPACE_KEY_CODE:
            space_pressed = True

    return rows_direction, columns_direction, space_pressed


def get_frame_size(text):
    """Calculate size of multiline text fragment. Returns pair (rows number, colums number)"""

    lines = text.splitlines()
    rows = len(lines)
    columns = max([len(line) for line in lines])
    return rows, columns


if __name__ == '__main__':
    rocket_frames = []
    for number in range(1, 3):
        with open(f'./animations/rocket_frame_{number}.txt', 'r') as file:
            rocket_frames.append(file.read())

    curses.update_lines_cols()
    curses.wrapper(draw)
