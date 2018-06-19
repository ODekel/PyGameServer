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
        heroes = {player.hero for player in players}
        for player in players:
            collision_detection(player, player.hero, heroes)
        pygame.time.Clock().tick(ITERATIONS_PER_SECOND)


def collision_detection(player, hero, heroes):
    """Runs the pygame spritecollide and handles it."""
    global COLLISION_DICT
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
    COLLISION_DICT.pop(hero, None)
    player.kill("YOU DIED")


if __name__ == '__main__':
    main()
