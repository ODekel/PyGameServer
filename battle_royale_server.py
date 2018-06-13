import pygame
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
    my_game.change_game_function(game_func, my_game)
    my_game.start_match()


def game_func(my_game):
    """Runs all the game's systems and interaction between players.
    Will run infinitely until stopped.
    If stopped, will stop all other processes of the, since the game can't run without this function running."""
    my_game.__match = True
    while my_game.__match:
        players = my_game.get_state()
        heroes = [player.hero for player in players]
        for player in players:
            collision_detection(player, player.hero, heroes)


def collision_detection(player, hero, heroes):
    """Runs the pygame spritecollide and handles it."""
    if pygame.sprite.spritecollideany(hero, [sprite for sprite in heroes if sprite != hero]) is not None:
        player.kill("YOU DIED")


if __name__ == '__main__':
    main()
