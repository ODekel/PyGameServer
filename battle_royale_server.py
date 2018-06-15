import pygame
import imp
game = imp.load_source("game", "modules\\server_game.py")
Game = game.Game

ITERATIONS_PER_SECOND = 30  # How many times will game_func run each second.
COLLISION_DICT = {}
# each player's hero is in the dictionary,
# pointing to a set of other players he collided with last iteration.


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
        pygame.time.Clock().tick(ITERATIONS_PER_SECOND)


def collision_detection(player, hero, heroes):
    """Runs the pygame spritecollide and handles it."""
    collided = pygame.sprite.spritecollideany(hero, [sprite for sprite in heroes if sprite != hero])
    if collided is not None:
        handle_collision(player, hero, collided)


def handle_collision(player, hero, collided):
    """Handles what happens when two players in the game collide.
    Returns True any change to game data was made, False otherwise."""
    global COLLISION_DICT
    if collided in COLLISION_DICT[hero]:
        return
    handle_dict(hero, collided)
    hero.health -= collided.damage
    if hero.health <= 0:
        COLLISION_DICT.pop(hero, None)
        player.kill("YOU DIED")


def handle_dict(hero, collided):
    """Handles the dict in case of a collide"""
    global COLLISION_DICT
    try:
        COLLISION_DICT[hero].add(collided)
    except KeyError:
        COLLISION_DICT[hero] = {collided}



if __name__ == '__main__':
    main()
