import pygame
import sys
import imp
game = imp.load_source("game", "modules\\server_game.py")
Game = game.Game

ITERATIONS_PER_SECOND = 30  # How many times will game_func run each second.
COLLISION_DICT = {}
# each player's hero is in the dictionary,
# pointing to a set of other players he collided with last iteration.

# GAME ATTRIBUTES
IP = "0.0.0.0"
CONNECTION_PORT = 5233
GAME_PORT = 16728
GAME_MAP = "assets\\dungeon_map.jpg"
SPAWN_LOC = (1000, 1000)
MAX_PLAYERS = 3


def main():
    """The main method for the game server."""
    my_game = Game(IP, CONNECTION_PORT, GAME_PORT, GAME_MAP, SPAWN_LOC, MAX_PLAYERS)
    my_game.change_game_function(game_func, my_game)
    my_game.start_match()


def game_func(my_game):
    """Runs all the game's systems and interaction between players.
    Will run infinitely until stopped.
    If stopped, will stop all other processes of the, since the game can't run without this function running."""
    while my_game.match:
        players = my_game.get_state()
        if game_over(players):
            handle_game_over(players)
        heroes = {player.hero for player in players}
        for player in players:
            collision_detection(player, player.hero, heroes)
        pygame.time.Clock().tick(ITERATIONS_PER_SECOND)


def game_over(players):
    """
    :param players: All the players in the game.
    :return: True if game is over, False otherwise.
    """
    return True if len(players) == 1 else False


def handle_game_over(players):
    """
    Handles the ending of the game than exits program. Assumes 1 player in players.
    :param players: All the players in game when it is over.
    :return: None.
    """
    players[0].kill("YOU WIN")
    sys.exit(0)


def collision_detection(player, hero, heroes):
    """Runs the pygame spritecollide and handles it."""
    heroes.remove(hero)
    handle_collision(player, hero, heroes, set(pygame.sprite.spritecollide(hero, heroes, False)))
    heroes.add(hero)


def handle_collision(player, hero, heroes, colliders):
    """Handles what happens to the players that collide with hero in the game."""
    global COLLISION_DICT
    try:
        COLLISION_DICT[hero] -= (set(heroes) - colliders)  # Remove all those who didn't collide.
    except KeyError:
        COLLISION_DICT[hero] = colliders
    else:
        colliders -= COLLISION_DICT[hero]   # Use only players that only collided with hero now.
        COLLISION_DICT[hero].update(colliders)   # Add colliders to COLLISION_DICT[hero]
    for collided in colliders:
        handle_damage(hero, collided)
    if hero.health <= 0:
        handle_death(player, hero)


def handle_damage(taker, dealer):
    """Handles the damage one character deals to another."""
    taker.health -= dealer.damage


def handle_death(player, hero):
    """Handles the killing of a player."""
    global COLLISION_DICT
    COLLISION_DICT.pop(hero, None)
    player.kill("YOU DIED")


if __name__ == '__main__':
    main()
