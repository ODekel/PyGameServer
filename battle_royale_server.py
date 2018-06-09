import imp
game = imp.load_source("game", "modules\\server_game.py")
Game = game.Game


def main():
    """The main method for the game server."""
    ip = "0.0.0.0"
    connection_port = 5233
    game_port = 16728
    game_map = "assets\\dungeon_map.jpg"
    spawn_loc = (1000, 1000)
    my_game = Game(ip, connection_port, game_port, game_map, spawn_loc)
    my_game.start_match()


if __name__ == '__main__':
    main()
