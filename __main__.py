from atexit import register
from copy import deepcopy
from json import dumps, load
from os import path, remove
from re import fullmatch
from time import sleep
from types import NoneType

register(lambda: print("\033[?7h"))

SCRIPT_DIR = path.dirname(path.abspath(__file__))

debug = False


class Category:
    def __init__(self, dataset):
        for key, value in dataset.items():
            setattr(self, key, Category(value) if isinstance(value, dict) else value)


class Text:
    def __init__(self, lang):
        self.lang = lang
        with open(
            path.join(SCRIPT_DIR, "languages", f"{lang}.json"), "r", encoding="utf-8"
        ) as file:
            text_json = load(file)
            for key, value in Category(text_json).__dict__.items():
                setattr(self, key, value)


t = Text("de")


class Settings:
    with open(path.join(SCRIPT_DIR, "settings", "default.json")) as file:
        default_settings = load(file)

    class New:
        def update_current_settings(dataset, current_data):
            for key, value in dataset.items():
                if isinstance(value, dict):
                    Settings.New.update_current_settings(value, current_data[key])
                else:
                    current_data[key] = value

        def __init__(self, load_save):
            current_settings = deepcopy(Settings.default_settings)
            if load_save:
                try:
                    with open(
                        path.join(SCRIPT_DIR, "settings", "saved_settings.json")
                    ) as saved_settings_file:
                        saved_settings = load(saved_settings_file)
                except FileNotFoundError:
                    pass
                else:
                    Settings.New.update_current_settings(
                        saved_settings, current_settings
                    )

            for key, value in Category(current_settings).__dict__.items():
                setattr(self, key, value)

            Settings.Save.changes = True
            Settings.Save.update_changes(self)

    class Save:
        changes = True
        changed_settings = {}

        def get_changes(obj, reference_dict, change_dict):
            obj_dict = deepcopy(obj).__dict__
            for key, value in obj_dict.items():
                if isinstance(value, (str, int, bool, list)):
                    if value != reference_dict[key]:
                        change_dict[key] = value
                else:
                    change_dict[key] = {}
                    Settings.Save.get_changes(
                        value, reference_dict[key], change_dict[key]
                    )
                    if change_dict[key] == {}:
                        del change_dict[key]
            return change_dict

        def update_changes(settings_obj=None):
            if settings_obj is None:
                settings_obj = settings
            if Settings.Save.changes:
                Settings.Save.changed_settings = Settings.Save.get_changes(
                    settings_obj, Settings.default_settings, {}
                )
                Settings.Save.changes = False

        def file():
            Settings.Save.update_changes()

            if Settings.Save.changed_settings != {}:
                with open(
                    path.join(SCRIPT_DIR, "settings", "saved_settings.json"), "w"
                ) as settings_save_file:
                    settings_save_file.write(
                        dumps(Settings.Save.changed_settings, indent=4)
                    )

        def delete():
            remove(path.join(SCRIPT_DIR, "settings", "saved_settings.json"))
            Settings.Save.changes = True

        def reset():
            global settings
            settings = Settings.New(False)
            Settings.Save.changes = True

    class Players:
        def new():
            settings.display.players.append({})
            Settings.Players.rename(-1, t.menu.player.new.char_prompt)
            Settings.Save.changes = True

        def rename(player_index, prompt=t.menu.player.rename.prompt):
            type_obj = Game.Input.input_type(str, 1, 1)
            print("\033[1F\033[K", end="")
            settings.display.players[player_index]["char"] = Game.Input.valid_input(
                prompt, Game.Input.range_error_msg(type_obj), type_obj
            )
            Settings.Save.changes = True

        def recolor(player_index, col):
            settings.display.players[player_index]["col"] = col
            Settings.Save.changes = True

        def extended_recolor(
            player_index,
            prompt=t.menu.player.recolor.prompt,
            error_msg=t.menu.general.input.error,
        ):
            Menu.Display.clear_screen()
            Menu.Display.All_colors.render()

            new_col = Game.Input.valid_input(
                prompt, error_msg, Game.Input.input_type(int, 0, 255)
            )

            Settings.Players.recolor(player_index, new_col)
            Settings.Save.changes = True

        def delete(player_index):
            settings.display.players.pop(player_index)
            Settings.Save.changes = True

    class General:
        def change_setting(
            setting_obj, key, type_obj, prompt=t.menu.settings.change.prompt
        ):
            print("\033[1F", end="")
            new_val = Game.Input.valid_input(
                prompt, Game.Input.range_error_msg(type_obj), type_obj
            )
            setattr(setting_obj, key, new_val)
            Settings.Save.changes = True


settings = Settings.New(__name__ == "__main__")


class Game:
    class State:
        def __init__(self):
            Game.State.current_player = 0
            Game.State.reset_grid()

        def reset_grid():
            grid = []
            for a in range(settings.map.rows):
                row = []
                for b in range(settings.map.collums):
                    row.append(-1)
                grid.append(row)
            Game.State.grid = grid

    class Display:
        def fix_menu_len():
            if settings.map.rows > Menu.Display.max_len:
                print(end="\n" * (settings.map.rows - Menu.Display.max_len + 1))
                Menu.Display.max_len = settings.map.rows + 1

            Menu.Display.last_menu_len = Menu.Display.max_len - 1
            print("\033[1F", end="")

        def draw():
            display_str = ""
            collums_str = str(settings.map.collums)
            for x in range(settings.map.collums):
                display_str += (
                    f"{' ' * (len(collums_str) - len(str(x + 1)))}{x + 1} "
                    if Game.State.grid[0][x] == -1
                    else " " * (len(collums_str) + 1)
                )

            for list in Game.State.grid:
                display_str += f"\n{f'{" " * (len(str(len(list))) - 1)}{(" " * (len(str(len(list))))).join(map(Game.Display.grid_int_to_char, list))}'}"
            print(f"\033[{Menu.Display.last_menu_len + 1}A", end="")
            print(
                f"\033[2F\033[J\033[1B{display_str}",
                end="\n\n\n\033[1F",
            )

        def grid_int_to_char(grid_int):
            if grid_int == -1:
                return settings.display.placeholder
            return f"\033[{'1m' if grid_int == Game.State.current_player else ''}{Game.Display.colored_player_char(grid_int)}"

        def colored_player_char(player_index, player=False):
            return f"{f'{t.general.player} ' if player else ''}\033[38;5;{settings.display.players[player_index]['col']}m{settings.display.players[player_index]['char']}\033[0m"

        def animate_fall(row, collum, player_index):
            print(
                "\033[?25l",
                end=f"\033[{len(Game.State.grid) + 1}F\033[{collum * 2 + 1}C\033[1D",
            )

            player_char = Game.Display.grid_int_to_char(player_index)
            free_char = Game.Display.grid_int_to_char(-1)

            print(player_char, end="\033[1B", flush=True)
            sleep(0.2)
            for x in range(row - 1):
                print(end=f"\033[1A\033[1D{free_char}\033[1D\033[1B", flush=True)
                print(player_char, end="\033[1B", flush=True)
                sleep(0.2)
            print(
                "\033[?25h",
                end=f"\033[{3 if row == 0 else len(Game.State.grid) - row + 1}E",
            )

    class Controller:
        def run():
            Game.Display.fix_menu_len()
            Game.State()

            while True:
                Game.Display.draw()

                current_collum = Game.Controller.get_collum()
                current_row = Game.Controller.apply_gravity(current_collum)

                Game.Display.animate_fall(
                    current_row, current_collum, Game.State.current_player
                )

                Game.State.grid[current_row][current_collum] = Game.State.current_player

                # check win
                if Game.Controller.check_win(
                    current_row, current_collum, Game.State.current_player
                ):
                    print(
                        f"\033[1F{t.general.player} {settings.display.players[Game.State.current_player]['char']} {t.game.end.win}"
                    )
                    break

                # check draw
                if Game.State.grid[0].count(-1) == 0:
                    print(f"\r{t.game.end.draw} D:")
                    break

                # switch player
                Game.State.current_player = (Game.State.current_player + 1) % len(
                    settings.display.players
                )

            # Return to menu
            Game.Display.draw()
            input(f"{'Broken' if debug else ''}{t.game.end.enter} ")

        def get_collum():
            while True:
                chosen_collum = (
                    Game.Input.valid_input(
                        f"{t.game.input.prompt} {settings.display.players[Game.State.current_player]['char']}",
                        t.game.input.error.invalid,
                        Game.Input.input_type(int, 1, settings.map.collums),
                    )
                    - 1
                )

                print("\033[1F", end="")
                if Game.State.grid[0][chosen_collum] != -1:
                    print(
                        f"\033[1E{t.game.input.error.full}\033[1F", end="", flush=True
                    )
                else:
                    return chosen_collum

        def apply_gravity(collum):
            for x in range(len(Game.State.grid)):
                if Game.State.grid[x][collum] != -1:
                    return x - 1
            return len(Game.State.grid) - 1

        def check_win(row, collum, player):
            check_left = min(collum, settings.map.win)
            check_right = min(settings.map.collums - collum - 1, settings.map.win)
            check_up = min(row, settings.map.win)
            check_down = min(settings.map.rows - row - 1, settings.map.win)
            x_count = 0
            y_count = 0
            x_y_count = 0
            mirror_x_y_count = 0

            for x in range(row - check_up, row + check_down + 1):
                y_count = y_count + 1 if Game.State.grid[x][collum] == player else 0
                if y_count >= settings.map.win:
                    return True

                for y in range(collum - check_left, collum + check_right + 1):
                    if x == row:
                        x_count = (
                            x_count + 1 if Game.State.grid[row][y] == player else 0
                        )
                        if x_count >= settings.map.win:
                            return True

                    if row - x == collum - y:
                        x_y_count = (
                            x_y_count + 1 if Game.State.grid[x][y] == player else 0
                        )
                        if x_y_count >= settings.map.win:
                            return True

                    if x - row == collum - y:
                        mirror_x_y_count = (
                            mirror_x_y_count + 1
                            if Game.State.grid[x][y] == player
                            else 0
                        )
                        if mirror_x_y_count >= settings.map.win:
                            return True

    class Input:
        
        def valid_input(prompt, error_msg, type_obj):
            while True:
                user_input = input(f"{prompt}: ")

                if type_obj.type is int and bool(fullmatch(r"\d+", user_input)):
                    input_int = int(user_input)
                    if (type_obj.min <= input_int) and (
                        (input_int <= type_obj.max) if (type(type_obj.max) is int) else True
                    ):
                        return input_int
                if (
                    type_obj.type is str
                    and type_obj.min <= len(user_input)
                    and (
                        len(user_input) <= type_obj.max
                        if isinstance(type_obj.max, int)
                        else True
                    )
                ):
                    return user_input

                print(f"\033[K{error_msg}\033[1F\033[2K", end="", flush=True)
            #return Game.Input.valid_input(prompt, error_msg, type_obj)

        class input_type:
            def __init__(self, type, min, max):
                self.type = type
                self.min = min
                self.max = max

        def range_error_msg(type_obj):
            return f"{getattr(t.menu.settings.change.error, 'int' if type_obj.type is int else 'str')} {f'{t.menu.settings.change.error.min} {type_obj.min}' if type_obj.max is False else f'{t.menu.settings.change.error.range} {type_obj.min} {t.menu.settings.change.error.range_and} {type_obj.max}'} {t.menu.settings.change.error.end}"


class Menu:
    class Option:
        def __init__(
            self,
            text,
            next_menu=False,
            next_args=(),
            value=None,
            func=None,
            func_args=(),
        ):
            self.text = f"{text}{'' if value is None else f': {value}'}"
            self.next_menu = next_menu
            if func is None:
                self.func = None
            else:
                self.func = lambda: func(*func_args)
            self.next_args = next_args

        def __str__(self):
            return f'Menu.Option object: "{self.__dict__}"'

    class Load:
        def default_values(menu_obj):
            menu_obj_default_values = {
                "header": "",
                "options": (),
                "append": "",
                "input_prompt": t.menu.general.input.prompt,
                "input_error_msg": t.menu.general.input.error,
            }
            unasigned_keys = menu_obj_default_values.keys() - menu_obj.__dict__.keys()

            for key in unasigned_keys:
                setattr(menu_obj, key, menu_obj_default_values[key])

            if not isinstance(menu_obj.options, tuple):
                menu_obj.options = tuple(menu_obj.options)

        # Selelectors
        class Main:
            def __init__(self):
                self.header = t.menu.main.header
                self.options = (
                    Menu.Option(t.menu.main.new_game, func=Game.Controller.run),
                    Menu.Option(t.menu.settings.header, "Settings"),
                    Menu.Option(t.menu.main.quit, None),
                )
                Menu.Load.default_values(self)

        class Settings:
            def __init__(self):
                self.header = t.menu.settings.header
                self.options = (
                    Menu.Option(t.menu.general.back, "Main"),
                    Menu.Option(t.menu.save.header, "Save"),
                    Menu.Option(t.menu.player.header, "Players"),
                    Menu.Option(t.menu.settings.general.header, "General_Settings"),
                )
                Menu.Load.default_values(self)

        # Save Menus
        class Save:
            def __init__(self, append=""):
                self.header = t.menu.save.header
                self.options = [
                    Menu.Option(t.menu.general.back, "Settings"),
                    Menu.Option(
                        t.menu.save.save.header,
                        "Save",
                        next_args=(t.menu.save.save.append,),
                        func=Settings.Save.file,
                    ),
                ]

                if (
                    path.exists(
                        path.join(SCRIPT_DIR, "settings", "saved_settings.json")
                    )
                    or Settings.Save.changed_settings != {}
                ):
                    self.options.append(
                        Menu.Option(t.menu.save.reset.header, "Reset_Save")
                    )

                self.append = append
                Menu.Load.default_values(self)

        class Reset_Save:
            def __init__(self):
                self.header = t.menu.save.reset.header
                self.options = [Menu.Option(t.menu.general.back, "Save")]
                if path.exists(
                    path.join(SCRIPT_DIR, "settings", "saved_settings.json")
                ):
                    self.options.append(
                        Menu.Option(
                            t.menu.save.reset.delete.text, func=Settings.Save.delete
                        )
                    )
                if Settings.Save.changed_settings != {} or debug:
                    self.options.append(
                        Menu.Option(
                            t.menu.save.reset.reset.text, func=Settings.Save.reset
                        )
                    )

                Menu.Load.default_values(self)

        # Player Menus
        class Players:
            def __init__(self):
                self.header = t.menu.player.header
                self.options = (
                    Menu.Option(t.menu.general.back, "Settings"),
                    *[
                        Menu.Option(
                            Game.Display.colored_player_char(index, True),
                            next_menu="Player_Config",
                            next_args=(index,),
                        )
                        for index in range(len(settings.display.players))
                    ],
                    Menu.Option(
                        t.menu.player.new.header,
                        "Player_Col",
                        next_args=(-1,),
                        func=Settings.Players.new,
                    ),
                )
                Menu.Load.default_values(self)

        class Player_Config:
            def __init__(self, player_index):
                player = settings.display.players[player_index]
                self.header = f"{t.menu.player.header}: {t.menu.player.player} \033[38;5;{player['col']}m{player['char']}\033[0m"
                self.options = [
                    Menu.Option(t.menu.general.back, "Players"),
                    Menu.Option(
                        t.menu.player.rename.header,
                        func=Settings.Players.rename,
                        func_args=(player_index,),
                    ),
                    Menu.Option(
                        t.menu.player.recolor.header,
                        "Player_Col",
                        next_args=(player_index,),
                    ),
                ]

                if len(settings.display.players) > 1:
                    self.options.append(
                        Menu.Option(
                            t.menu.player.delete.header,
                            "Player_Delete",
                            next_args=(player_index,),
                        )
                    )
                Menu.Load.default_values(self)

        class Player_Col:
            def __init__(self, player_index):
                self.header = t.menu.player.recolor.header
                self.options = [
                    *[
                        Menu.Option(
                            f"\033[{9 if color == 0 else 3}{color}m{
                                getattr(
                                    t.menu.player.recolor.colors,
                                    [
                                        'black',
                                        'red',
                                        'green',
                                        'yellow',
                                        'blue',
                                        'magenta',
                                        'cyan',
                                        'white',
                                    ][color],
                                )
                            }\033[0m",
                            "Player_Config",
                            next_args=(player_index,),
                            func=Settings.Players.recolor,
                            func_args=(player_index, color),
                        )
                        for color in range(8)
                    ],
                    Menu.Option(
                        t.menu.player.recolor.colors.more,
                        "Player_Config",
                        next_args=(player_index,),
                        func=Settings.Players.extended_recolor,
                        func_args=(player_index,),
                    ),
                ]

                if True:
                    self.options.insert(
                        0,
                        Menu.Option(
                            t.menu.general.back,
                            "Player_Config",
                            next_args=(player_index,),
                        ),
                    )

                Menu.Load.default_values(self)

        class Player_Delete:
            def __init__(self, player_index):
                self.header = f"{t.menu.player.delete.prompt.start} {Game.Display.colored_player_char(player_index, True)}\033[1m {t.menu.player.delete.prompt.end}"
                self.options = (
                    Menu.Option(
                        t.general.y,
                        "Players",
                        func=Settings.Players.delete,
                        func_args=(player_index,),
                    ),
                    Menu.Option(
                        t.general.n, "Player_Config", next_args=(player_index,)
                    ),
                )
                Menu.Load.default_values(self)

        # Misc Settings Menu
        class General_Settings:
            def __init__(self):
                self.header = t.menu.settings.general.header
                self.options = (
                    Menu.Option(t.menu.general.back, "Settings"),
                    Menu.Option(
                        t.menu.settings.general.free,
                        value=f'"{settings.display.placeholder}"',
                        func=Settings.General.change_setting,
                        func_args=(
                            settings.display,
                            "placeholder",
                            Game.Input.input_type(str, 1, 1),
                        ),
                    ),
                    Menu.Option(
                        t.menu.settings.general.collums,
                        value=settings.map.collums,
                        func=Settings.General.change_setting,
                        func_args=(
                            settings.map,
                            "collums",
                            Game.Input.input_type(int, 1, False),
                        ),
                    ),
                    Menu.Option(
                        t.menu.settings.general.rows,
                        value=settings.map.rows,
                        func=Settings.General.change_setting,
                        func_args=(
                            settings.map,
                            "rows",
                            Game.Input.input_type(int, 1, False),
                        ),
                    ),
                    Menu.Option(
                        t.menu.settings.general.win,
                        value=settings.map.win,
                        func=Settings.General.change_setting,
                        func_args=(
                            settings.map,
                            "win",
                            Game.Input.input_type(int, 1, False),
                        ),
                    ),
                )
                Menu.Load.default_values(self)

    class Display:
        max_len = 0
        last_menu_len = 0

        def clear_screen():
            print(f"\033[{Menu.Display.max_len + 2}F\033[0J", end="")

        def render(header, options, append):
            output_str = f"\033[1m{header}\033[0m"
            for x in range(len(options)):
                output_str += f"\n{x + 1}: {options[x].text}"
            Menu.Display.clear_screen()
            print(
                f"{output_str}{f'\033[{Menu.Display.max_len - len(options)}B' if Menu.Display.max_len > len(options) + 1 else '\n'}",
                end="",
            )
            print(end=f"\n\n{'' if append is False else append}\033[1F")
            Menu.Display.max_len = max(len(options) + 1, Menu.Display.max_len)

        class All_colors:
            current_menu_len = 0

            def color_square(
                width, height, start, format_specifier=">3", new_line=True
            ):
                Menu.Display.All_colors.current_menu_len += height if new_line else 0
                return [
                    " ".join(
                        [
                            f"\033[38;5;{y * width + x + start}m{format(y * width + x + start, format_specifier)}"
                            for x in range(width)
                        ]
                    )
                    for y in range(height)
                ]

            def render():
                Menu.Display.All_colors.current_menu_len = 0

                all_color_arr = []

                usr_color_arr = Menu.Display.All_colors.color_square(8, 2, 0)
                all_color_arr.append("\n".join(usr_color_arr))

                rgb_color_arr = [
                    "\n".join(
                        [
                            f"{
                                Menu.Display.All_colors.color_square(
                                    6, 1, 36 * r + 16 + index * 6
                                )[0]
                            } {
                                ' '.join(
                                    Menu.Display.All_colors.color_square(
                                        6, 1, 36 * r + 52 + index * 6, '<3', False
                                    )[0].split(' ')[::-1]
                                )
                            }"
                            for index in range(6)
                        ][:: 1 if r % 4 == 0 else -1]
                    )
                    for r in range(0, 6, 2)
                ]
                all_color_arr.append("\n".join(rgb_color_arr))

                grayscale_arr = Menu.Display.All_colors.color_square(8, 2, 240)
                all_color_arr.append("\n".join(grayscale_arr))

                print(f"{'\n'.join(all_color_arr)}", end="\n\n\n\033[1A")
                Menu.Display.max_len = max(
                    Menu.Display.max_len, Menu.Display.All_colors.current_menu_len
                )

    class Controller:
        def run():
            current_menu_name = "Main"
            current_menu_args = ()
            while current_menu_name is not None:
                current_menu = getattr(Menu.Load, current_menu_name)(*current_menu_args)
                Menu.Display.render(
                    header=current_menu.header,
                    options=current_menu.options,
                    append=current_menu.append,
                )
                selected_option = current_menu.options[
                    Game.Input.valid_input(
                        current_menu.input_prompt,
                        current_menu.input_error_msg,
                        Game.Input.input_type(int, 1, len(current_menu.options)),
                    )
                    - 1
                ]

                if selected_option.func is not None:
                    selected_option.func()

                if isinstance(selected_option.next_menu, (str, NoneType)):
                    current_menu_name = selected_option.next_menu
                    current_menu_args = selected_option.next_args


def main():
    if not debug:
        print("\033[?7l", end="")
    print("\n" * (Menu.Display.max_len + 2), flush=False)
    Menu.Controller.run()


if __name__ == "__main__":
    main()

"""
Todo:
    tttt
    layout:
        class Game
            class General
            class TTTT
            class 4InARow

    more text confirm like t menu save save append
"""
