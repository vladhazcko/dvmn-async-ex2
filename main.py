import asyncio
import curses
import time
import random
from itertools import cycle
from physics import update_speed
from obstacles import Obstacle
from curses_tools import draw_frame, get_frame_size
from explosion import explode

SPACE_KEY_CODE = 32
LEFT_KEY_CODE = 260
RIGHT_KEY_CODE = 261
UP_KEY_CODE = 259
DOWN_KEY_CODE = 258
BORDER = 1
PHRASES = {
    1957: "First Sputnik",
    1961: "Gagarin flew!",
    1969: "Armstrong got on the moon!",
    1971: "First orbital space station Salute-1",
    1981: "Flight of the Shuttle Columbia",
    1998: 'ISS start building',
    2011: 'Messenger launch to Mercury',
    2020: "Take the plasma gun! Shoot the garbage!",
}


def draw(canvas):
    curses.curs_set(False)
    canvas.border()
    canvas.nodelay(True)
    y_max, x_max = canvas.getmaxyx()
    y_min, x_min = canvas.getbegyx()
    ship_height, ship_width = get_frame_size(rocket_frames[0])
    star_height = star_width = 1

    global global_coroutines
    global_coroutines = [
        run_spaceship(canvas, y_max - ship_height - BORDER, (x_max - ship_width) // 2),
        animate_spaceship(),
        fill_orbit_with_garbage(canvas),
        show_current_year(canvas)
    ]

    stars_count = 50
    for _ in range(stars_count):
        row = random.randint(y_min + BORDER + star_height, y_max - BORDER - star_height)
        column = random.randint(x_min + BORDER + star_width, x_max - BORDER - star_width)
        symbol = random.choice(['*', '+', '.', ':'])
        global_coroutines.append(
            blink(canvas, row, column, symbol)
        )

    while True:
        for coroutine in global_coroutines.copy():
            try:
                coroutine.send(None)
            except StopIteration:
                global_coroutines.remove(coroutine)
        canvas.refresh()
        time.sleep(0.1)


async def blink(canvas, row, column, symbol='*'):
    """Display animation of star"""
    while True:
        delay = random.randint(0, 30)
        await sleep(delay)

        canvas.addstr(row, column, symbol, curses.A_DIM)
        await sleep(20)

        canvas.addstr(row, column, symbol)
        await sleep(3)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        await sleep(5)

        canvas.addstr(row, column, symbol)
        await sleep(3)


async def fire(canvas, start_row, start_column, rows_speed=-2, columns_speed=0):
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
        for obstacle in global_obstacles:
            if obstacle.has_collision(row, column):
                global_obstacles_in_last_collisions.append(obstacle)
                return
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


async def animate_spaceship():
    global global_spaceship_frame
    for rocket_frame in cycle(rocket_frames):
        global_spaceship_frame = rocket_frame
        await asyncio.sleep(0)


async def run_spaceship(canvas, row, column):
    ship_height, ship_width = get_frame_size(rocket_frames[0])
    delta_y, delta_x = canvas.getmaxyx()
    y_min, x_min = canvas.getbegyx()
    y_max, x_max = y_min + delta_y - ship_height - 1, x_min + delta_x - ship_width - 1
    year_of_the_gun = 2020

    global global_coroutines
    while True:
        dy, dx, is_click_space_btn = read_controls(canvas)

        row = min(row + dy, y_max) if dy > 0 else max(y_min + 1, row + dy)
        column = min(column + dx, x_max) if dx > 0 else max(x_min + 1, column + dx)

        if is_click_space_btn and global_year >= year_of_the_gun:
            fire_coroutine = fire(canvas, row, column + ship_width // 2)
            global_coroutines.append(fire_coroutine)

        current_frame = global_spaceship_frame
        draw_frame(canvas, row, column, current_frame)
        await asyncio.sleep(0)

        draw_frame(canvas, row, column, current_frame, negative=True)
        for obstacle in global_obstacles:
            if obstacle.has_collision(row, column):
                await show_gameover(canvas)
                return


async def fly_garbage(canvas, column, garbage_frame, speed=0.2):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same, as specified on start."""
    rows_number, columns_number = canvas.getmaxyx()
    row_size, column_size = get_frame_size(garbage_frame)

    column = max(column, 0)
    column = min(column, columns_number - 1)

    row = 0

    obstacle = Obstacle(row, column, row_size, column_size)
    global_obstacles.append(obstacle)
    while row < rows_number:
        draw_frame(canvas, row, column, garbage_frame)
        await asyncio.sleep(0)

        draw_frame(canvas, row, column, garbage_frame, negative=True)
        if obstacle in global_obstacles_in_last_collisions:
            global_obstacles_in_last_collisions.remove(obstacle)
            await explode(canvas, row + row_size // 2, column + column_size // 2)
            return
        row += speed
        obstacle.row = row

    global_obstacles.remove(obstacle)


async def fill_orbit_with_garbage(canvas):
    garbage_coroutines = []
    while not get_garbage_delay_tics(global_year):
        await asyncio.sleep(0)

    while True:
        y_max, x_max = canvas.getmaxyx()
        y_min, x_min = canvas.getbegyx()

        garbage_frame = random.choice(garbage_frames)
        garbage_height, garbage_width = get_frame_size(garbage_frame)

        x_start = x_min + garbage_width + BORDER
        x_end = x_max - garbage_width - BORDER
        column = random.randint(x_start, x_end)

        garbage_coroutine = fly_garbage(canvas, column, garbage_frame)
        garbage_coroutines.append(garbage_coroutine)

        count_steps_to_add_coroutine = get_garbage_delay_tics(global_year)
        for _ in range(count_steps_to_add_coroutine):
            for garbage_coroutine in garbage_coroutines.copy():
                try:
                    garbage_coroutine.send(None)
                except StopIteration:
                    garbage_coroutines.remove(garbage_coroutine)
            await asyncio.sleep(0)


async def show_gameover(canvas):
    y_max, x_max = canvas.getmaxyx()
    y_min, x_min = canvas.getbegyx()
    gameover_frame = random.choice(gameover_frames)
    y_size, x_size = get_frame_size(gameover_frame)

    row = max((y_max - y_min - y_size) // 2, 0)
    column = max((x_max - x_min - x_size) // 2, 0)

    while True:
        draw_frame(canvas, row, column, gameover_frame)
        await asyncio.sleep(0)


async def show_current_year(canvas):
    y_max, x_max = canvas.getmaxyx()
    row = y_max - BORDER
    column = x_max // 2
    tics_for_sleep = 15

    global global_year
    while True:
        text = f'_Current_year:{global_year}_{PHRASES.get(global_year, "")}'
        draw_frame(canvas, row, column, text)
        await sleep(tics_for_sleep)
        draw_frame(canvas, row, column, text, negative=True)
        global_year += 1


def read_controls(canvas):
    """Read keys pressed and returns tuple witl controls state."""

    rows_direction = columns_direction = 0
    space_pressed = False
    row_speed = column_speed = 0

    while True:
        pressed_key_code = canvas.getch()

        if pressed_key_code == -1:
            # https://docs.python.org/3/library/curses.html#curses.window.getch
            break

        if pressed_key_code == UP_KEY_CODE:
            row_speed, column_speed = update_speed(row_speed, column_speed, -1, 0)

        if pressed_key_code == DOWN_KEY_CODE:
            row_speed, column_speed = update_speed(row_speed, column_speed, 1, 0)

        if pressed_key_code == RIGHT_KEY_CODE:
            row_speed, column_speed = update_speed(row_speed, column_speed, 0, 1)

        if pressed_key_code == LEFT_KEY_CODE:
            row_speed, column_speed = update_speed(row_speed, column_speed, 0, -1)

        if pressed_key_code == SPACE_KEY_CODE:
            space_pressed = True

        rows_direction += row_speed
        columns_direction += column_speed

    return rows_direction, columns_direction, space_pressed


async def sleep(tics=1):
    for _ in range(tics):
        await asyncio.sleep(0)


def get_garbage_delay_tics(year):
    if year < 1961:
        return None
    elif year < 1969:
        return 20
    elif year < 1981:
        return 14
    elif year < 1995:
        return 10
    elif year < 2010:
        return 8
    elif year < 2020:
        return 6
    else:
        return 2


def get_frames_by_file(file_paths):
    frames = []

    for file_path in file_paths:
        with open(f'./animations/{file_path}', 'r') as file:
            frames.append(file.read())
    return frames


if __name__ == '__main__':
    rocket_files = [
        'rocket_frame_1.txt',
        'rocket_frame_2.txt'
    ]
    garbage_files = [
        'duck.txt',
        'hubble.txt',
        'lamp.txt',
        'trash_large.txt',
        'trash_small.txt',
        'trash_xl.txt'
    ]
    gameover_files = [
        'gameover1.txt',
        'gameover2.txt'
    ]
    rocket_frames = get_frames_by_file(rocket_files)
    garbage_frames = get_frames_by_file(garbage_files)
    gameover_frames = get_frames_by_file(gameover_files)

    global_spaceship_frame = rocket_frames[0]
    global_coroutines = []
    global_obstacles = []
    global_obstacles_in_last_collisions = []
    global_year = 1957

    curses.update_lines_cols()
    curses.wrapper(draw)
