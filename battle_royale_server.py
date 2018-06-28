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
    started = 0
    games = get_num_of_games()
    while games == 0 or started < games:
        my_game = Game(IP, CONNECTION_PORT, GAME_PORT, GAME_MAP, SPAWN_LOC, MAX_PLAYERS)
        my_game.change_game_function(game_func, my_game)
        my_game.start_match()
        try:
            started += 1
        except ValueError:
            started = 0    # If program got here, it means it should run infinitely and reached int limit.


def get_num_of_games():
    """Returns the number of games the caller wants to run."""
    try:
        num_of_games = int(raw_input("Number of games to run (0 for infinite): "))
        if num_of_games < 0:
            raise ValueError
    except ValueError:
        raw_input("Please enter a valid number. Press Enter to exit.")
        sys.exit(0)
    return num_of_games


def game_func(my_game):
    """Runs all the game's systems and interaction between players.
    Will run infinitely until stopped.
    If stopped, will stop all other processes of the, since the game can't run without this function running."""
    prepare_match(my_game)
    while my_game.match:
        players = my_game.get_state()
        if game_over(players):
            handle_game_over(players)
            break
        heroes = {player.hero for player in players}
        for player in players:
            collision_detection(player, player.hero, heroes)
        pygame.time.Clock().tick(ITERATIONS_PER_SECOND)


def prepare_match(my_game):
    """Handles the preparations for the match."""
    global COLLISION_DICT
    players = my_game.get_state()
    for player in players:
        COLLISION_DICT[player.hero] = set(p.hero for p in players)  # Spawn doesn't count


def game_over(players):
    """
    :param players: All the players in the game.
    :return: True if game is over, False otherwise.
    """
    return True if len(players) <= 1 else False


def handle_game_over(players):
    """
    Handles the ending of the game than exits program. Assumes 1 or no players in players.
    :param players: All the players in game when it is over.
    :return: None.
    """
    try:
        players[0].kill("YOU WIN!")
    except IndexError:
        pass    # Game ended with no winners.


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
