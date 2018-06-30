import math
import socket
import threading
from sys import exit as sysexit
from os import path
from PIL import Image
import time
import pickle
import copy
import pygame
import random
import imp
character = imp.load_source("character", "modules\\character.py")
Character = character.Character
func = imp.load_source("function", "modules\\function.py")
GameFunction = func.GameFunction

DEBUG = False
print_lock = threading.Lock()


class Game(object):
    """Represents an object used to store data and help control a game."""
    __inactive_time_kick = 30
    red_team = "RED"
    blue_team = "BLUE"

    # @property
    # def inactive_time_kick(self):
    #     return Game.__inactive_time_kick

    def __init__(self, ip, connection_port, game_port, game_map, spawn_loc, max_players=0):
        """Create a new game object.
        ip is the ip the server will run on.
        connection_port is the port clients will communicate with to connect to the server.
        game_port is the lowest port to be used to communicate with a client during a game.
        game_map is the path to the file of the game map's image. Will raise an error if file isn't good.
        Should be the same name (path does not matter) on both the client and the server.
        spawn_loc is the location the player will spawn in (x, y).
        max_players is the maximum amount of players on the server at any given moment.
        If absent or 0 there is no limit."""
        # with open(Player.object_file, 'w+') as f:
        #     f.write(Character(r"assets\red_player.png", 3, 4, 1, 15, 1, 5, {}, spawn_loc).pickled_no_image())
        self.__ip = ip
        self.__socket = socket.socket()
        self._connection_port = connection_port
        self._game_port = game_port
        self.max_players = max_players
        self.__listen = False
        self.__match = False
        self.timeout = 0.1
        self.__game_map_name = game_map
        self.__game_map_size = Image.open(game_map).size
        self.__spawn_loc = spawn_loc
        self.__red_team = []
        self.__blue_team = []   # 2 teams if I want to make a 2 team game.
        self.__connected = 0    # All the players that have connected to the game.
        self.__game_func = GameFunction(self._default_game_func)
        self.__wait_for_players = True

    @property
    def wait_for_players(self):
        """If True (default), will wait for max_players to connect before starting the game.
        If False, will immediately start the game for any player that joins the game."""
        return self.__wait_for_players

    @wait_for_players.setter
    def wait_for_players(self, value):
        """If True (default), will wait for max_players to connect before starting the game.
        If False, will immediately start the game for any player that joins the game."""
        if self.__listen or self.__match:
            raise (AttributeError, "wait_for_player cannot be changed after the game started.")
        self.__wait_for_players = value

    def change_game_function(self, f, *args):
        """Changes the function that runs the game. change this to change how the game plays.
        Every change to the hero attributes of players in the game will be noticed by the running default loops.
        Uses the vars() built in function on the hero attribute.
        For the change to effect the game, this function MUST be called before start_match is called.
        The function should run in a loop until the game ends."""
        self.__game_func = GameFunction(f, *args)

    @property
    def match(self):
        """Get self.__match."""
        return self.__match

    def stop_match(self, msg):
        """Kills the match. All communication will stop and the server will stop running.
        msg will be displayed to the players when the game is killed."""
        self.__listen = False
        self.__match = False
        for player in self.__red_team + self.__blue_team:
            player.kill(msg)

    def get_state(self):
        """
        :return: A list with all player objects in game.
        """
        return copy.copy(self.__red_team + self.__blue_team)

    def get_player_attributes(self):
        """Return a dict with the players' attributes (vars)."""
        attributes = {}
        for player in self.get_state():
            attributes[player] = copy.deepcopy(vars(player.hero))
        return attributes

    def get_game_map_size(self):
        """Returns the game_map's size."""
        return copy.deepcopy(self.__game_map_size)

    def get_game_map_name(self):
        """Returns the game_map's file path."""
        return copy.deepcopy(self.__game_map_name.split("\\")[-1])

    def get_spawn_loc(self):
        """
        :return: The spawn loc on the map (x, y).
        """
        return copy.deepcopy(self.__spawn_loc)

    def get_index_red(self, player):
        """
        If player is not in the red team, will raise an error.
        :param player: The player to get index of.
        :return: The index of 'player' in the red team's set.
        """
        return self.__red_team.index(player)

    def get_index_blue(self, player):
        """
        If player is not in the blue team, will raise an error.
        :param player: The player to get index of.
        :return: The index of 'player' in the blue team's set.
        """
        return self.__blue_team.index(player)

    def start_match(self):
        """Start listening to new players connecting to the.
        Disconnects when the amount of players in game is reached.
        Runs the game."""
        self._start_listening()
        self.__match = True
        threading.Thread(target=self.__game_func).start()

    def _start_listening(self):
        """
        Blocking if self.wait_for_players is set to True, otherwise not blocking.
        This handled like that so that game will only start after all players connected if
        self.wait_for_players is set to True.
        :return: None.
        """
        if self.__wait_for_players:
            self.listen()
            while len(self.get_state()) < self.max_players:    # Wait for all threads to start.
                pass
        else:
            threading.Thread(target=self.listen).start()

    def listen(self):
        """Lets players connect to the server using the connection_port and game_port.
        Will not accept more players than max_players to the server."""
        player_threads = []    # Used if self.__wait_for_players is True.
        self.__socket.bind((self.__ip, self._connection_port))
        self.__socket.listen(self.max_players)
        self.__listen = True
        while self.__listen:
            if not self.is_game_filled():
                client_socket, client_addr = self.__socket.accept()
                print("Trying to connect: " + str(client_addr[0]))
                player = threading.Thread(target=self.handle_client, args=(client_socket, self._connection_port))
                self.__connected += 1
                self._handle_new_player_thread(client_socket, player, player_threads)
            else:
                self.__listen = False
                self._start_game_threads(player_threads)
        self.__listen = False
        self.__socket.close()
        self.__socket = socket.socket()

    def stop_listening(self):
        """Stop accepting new clients using connection_port. Stops the listen method."""
        self.__listen = False

    def is_game_filled(self):
        """
        :return: True when the amount of players that have connected reaches max_players, False otherwise.
        """
        return True if self.__connected >= self.max_players != 0 else False

    def _handle_new_player_thread(self, player_socket, player_thread, player_threads):
        """Does what should be done with a thread of a recently connected player.
        player_thread is the self.handle_client thread of the play.
        player_threads is the list of all previous threads."""
        if self.__wait_for_players:
            player_socket.sendall("WAITING")    # Tell the client the server is not yet full.
            player_threads.append(player_thread)
            return
        player_thread.start()

    def _start_game_threads(self, threads):
        if self.__wait_for_players:
            for t in threads:
                t.start()

    def handle_client(self, client_socket, port):
        """Starts the communication between a single client and the server."""
        if self.__wait_for_players:
            try:
                client_socket.sendall("CONTINUE")
            except socket.error:
                self.__disconnected_before_started(client_socket)
                return
        if Game.connect_to_client(client_socket, port) is None:
            return None
        player = Player.get_player_object(self, client_socket, Player.server_character)
        self.__add_to_game(player)
        print("Connected: " + str(client_socket.getsockname()[0]))
        self.__call_init_player_client(player)
        sender = threading.Thread(target=player.send_loop)
        receiver = threading.Thread(target=player.recv_loop)
        sender.start()
        receiver.start()
        sender.join()
        receiver.join()
        self.remove(player)

    def __disconnected_before_started(self, client):
        """This function should be called when the client disconnected before the game actually started."""
        with open(Player.object_file, 'r+') as f:
            dummy_character = pickle.load(f)
        dummy = Player(self, client, dummy_character, Game.red_team, 0, (0, 0))
        self.__add_to_game(dummy)  # Add a dummy to the game so it will start.
        while not self.__match:
            pass
        self.remove(dummy)    # Client should not be in the game.

    def _default_game_func(self):
        """Runs all the game's systems and interaction between players.
        If stopped, will stop all other processes of the, since the game can't run without this function running."""
        pass

    def __call_init_player_client(self, player):
        """Calls player.init_player_client with the right parameters."""
        if player.get_team() == Game.red_team:
            player.init_player_client(copy.copy(self.__red_team), copy.copy(self.__blue_team))
        elif player.get_team() == Game.blue_team:
            player.init_player_client(copy.copy(self.__blue_team), copy.copy(self.__red_team))

    def __add_to_game(self, player):
        """Add a player to a team.
        If the player is already part of one of the teams in the game, he will not be added."""
        if player.get_team() == Game.red_team:
            if player not in self.__red_team:
                self.__red_team.append(player)
        elif player.get_team() == Game.blue_team:
            if player not in self.__blue_team:
                self.__blue_team.append(player)
        # player.init_in_game()

    def remove(self, player):
        """
        Remove a given Player object from the game. Safe to call even if Player is not in game.
        :param player: A Player object to remove.
        :return: None.
        """
        try:
            self.__red_team.remove(player)
        except ValueError:
            try:
                self.__blue_team.remove(player)
            except ValueError:
                pass

    @staticmethod
    def connect_to_client(sock, port, timeout=socket.getdefaulttimeout()):
        """Connect to a client with an already established TCP connection. client_addr is the (ip, port) tuple.
        If connection to client could not be made, Returns None.
        If called by the connection port, returns None, and redirects the client to game_port.
        Otherwise, returns the sock that is connected to the client."""
        sock.settimeout(timeout)
        try:
            sock.sendall("GAME SERVER")
            debug_print("send ", "GAME SERVER", " - ", str(sock.getsockname()[0]))
            if sock.recv(1024) != "GAME CLIENT":
                raise socket.error
            debug_print("recv ", "GAME CLIENT", " - ", str(sock.getsockname()[0]))
            sock.sendall("CONNECTED " + str(port))
            debug_print("send ", "CONNECTED", " - ", str(sock.getsockname()[0]))
        except socket.error:
            could_not_connect(sock)
            return None
        if sock.getsockname()[1] == port:
            return sock
        return None


class Player(object):
    """Represents a client in a game."""

    object_file = "assets/player.brhr"
    server_character = "SERVER SIDE"
    client_character = "CLIENT SIDE"

    def __init__(self, game, sock, hero, team, fps, resolution):
        """Create a new Client object.
        game is the Game object the client is part of.
        sock is the socket used to communicate with the client.
        hero is the Character object of the player.
        team is the team the client is part of. RED for red team, BLUE for blue.
        fps is the refresh rate of the client's monitor.
        resolution is a tuple of (width, height) of the client's screen."""
        self.__game = game
        self.__sock = sock
        self.__hero = hero
        self.__team = team
        self.__fps = fps
        self.__resolution = resolution
        self._uppery = (self.__game.get_game_map_size()[1]) - (resolution[1] / 2)
        self._upperx = (self.__game.get_game_map_size()[0]) - (resolution[0] / 2)
        self._lowerx = resolution[0] / 2
        self._lowery = resolution[1] / 2
        self.__send = False
        self.__recv = False
        self.__game_attributes = {}
        self.__game_state = []
        self.sock_name = str(sock.getpeername()[0])

    @property
    def hero(self):
        return self.__hero

    def init_player_client(self, allies, enemies):
        """Must be called after adding the player object to the game (That was given to the constructor).
        allies and enemies are lists of players.
        Returns None."""
        self._send("ALLIES")
        self._send_by_size(pickle.dumps([player.hero for player in allies], pickle.HIGHEST_PROTOCOL), 32)
        self._send("ENEMIES")
        self._send_by_size(pickle.dumps([player.hero for player in enemies], pickle.HIGHEST_PROTOCOL), 32)
        self._send("HERO POS")
        self._send_by_size(str(allies.index(self)), 32)
        self.__update_game_attributes(self.__game.get_state(), self.__game.get_player_attributes())
        # Client is updated.

    def get_location(self):
        """
        :return: The location of the player on the game_map. (x, y)
        """
        return copy.deepcopy(self.__hero.rect.center)

    def get_team(self):
        """
        :return: The team the player is in. Should be a string.
        """
        return copy.deepcopy(self.__team)

    def get_map_name(self):
        return self.__game.get_game_map_name()

    def _send(self, s):
        """
        Sends the string to the client.
        :param s: A string to send to the client.
        :return: None.
        """
        self.__sock.sendall(s)

    def _send_by_size(self, s, header_size):
        """
        Sends by size to the client.
        :param s: A string to send to the client.
        :param header_size: The size (in bytes) of the header.
        :return: None.
        """
        self.__sock.sendall(str(len(s)).zfill(header_size))
        self.__sock.sendall(s)

    def _recv(self, size):
        """
        Receive a string from the client.
        :param size: The size (in bytes) to receive. Max.
        :return: The string received.
        """
        return self.__sock.recv(size)

    def _recv_by_size(self, header_size):
        """
        Receive by size a string from the client.
        If an empty string is received (ie, the other side disconnected), an empty string will be returned.
        :param header_size: The size (in bytes) of the header.
        :return: The string received.
        """
        str_size = ""
        str_size += self.__sock.recv(header_size)
        if str_size == "":
            return ""

        while len(str_size) < header_size:
            str_size += self.__sock.recv(header_size - len(str_size))
        size = int(str_size)

        data = ""
        while len(data) < size:
            data += self.__sock.recv(size - len(data))
        return data

    def receive_player_data(self):
        """
        Receives data from the player. Recommended to wrap this function in a try/except with socket.error.
        If data cannot be unpickled, will return raw data.
        :return: The data received as a pygame.key.pressed object.
        """
        data = self._recv_by_size(32)
        try:
            return pickle.loads(data)
        except (pickle.UnpicklingError, KeyError):
            return data

    def handle_player_data(self, pickled_pressed):
        """
        Applies data to the game the player is part of, once.
        pressed is a pygame.key.pressed object.
        Compatible with receive_player_data method.
        :return: None.
        """
        pressed = pickle.loads(pickled_pressed)
        newy = self.__hero.rect.centery
        newx = self.__hero.rect.centerx
        if pressed[pygame.K_w]:
            newy -= self.__hero.speed
        if pressed[pygame.K_a]:
            newx -= self.__hero.speed
        if pressed[pygame.K_s]:
            newy += self.__hero.speed
        if pressed[pygame.K_d]:
            newx += self.__hero.speed
        elif newx != self.__hero.rect.centerx and newy != self.__hero.rect.centery:
            newx, newy = self._fix_diagonal_movement(newx, newy)
        self.__hero.rect.center = (self._updatex(newx), self._updatey(newy))

    def recv_loop(self):
        """
        Will run until stopped, receiving data from the player and updating attributes accordingly.
        When stopped by the server or the client, will delete the player from the game.
        This function receives everything the game needs to run correctly, but does not add the rules of the game.
        :return: None.
        """
        self.__recv = True
        cnt = 0
        self.__sock.settimeout(self.__game.timeout)
        while self.__recv:
            try:
                data = self._recv_by_size(32)
            except socket.timeout:
                pass
            except socket.error:
                self.__recv = False
            except AttributeError:
                if self.__sock is None:
                    self.__recv = False
            else:
                if data == "" or data == "DISCONNECT":
                    break
                debug_print("recv: %s - %s" % (cnt, self.sock_name))
                cnt += 1
                self.handle_player_data(data)
            # pygame.time.Clock().tick(self.__fps)
        self.__recv = False
        self.__send = False
        self.remove()

    def send_loop(self):
        """
        Will run until stopped, sending data to the player.
        When stopped by the server or the client, will delete the player from the game.
        This function sends everything the game needs to run correctly, but does not add the rules of the game.
        :return: None.
        """
        self.__send = True
        self.__sock.settimeout(self.__game.timeout)
        cnt = 0
        snd_cnt = 0
        while self.__send:
            current_state = self.__game.get_state()
            current_attributes = self.__game.get_player_attributes()
            try:
                send = self.__add_send_updates(current_attributes)
            except AttributeError:
                break   # Another thread removed this object while loop was running.
            try:
                if send != "":
                    self._send_by_size(send, 32)
                    debug_print("sent: %s(%s) - %s" % (cnt, snd_cnt, self.sock_name))
                    snd_cnt += 1
            except socket.error:
                break
            self.__update_game_attributes(current_state, current_attributes)
            cnt += 1
            pygame.time.Clock().tick(self.__fps)
        self.__send = False
        self.__recv = False
        self.remove()

    def __update_game_attributes(self, current_state, current_attributes):
        """Updates self.__game_attributes and self.__locations.
        current_attributes is self.__game.get_attributes used in last loop."""
        self.__game_state = current_state
        self.__game_attributes = current_attributes

    def __add_send_updates(self, current_attributes):
        """
        Returns a string to send to the client,
        according to a protocol and the changes between current_attributes and self.__game_attributes.
        :param current_attributes: The current state of the game as received from Game.get_player_attributes().
        :return: The string to send to the client for updates.
        """
        send = self.__add_del_updates(current_attributes)
        for player in current_attributes:
            if player in self.__game_attributes:
                for key, value in current_attributes[player].iteritems():
                    if self.__game_attributes[player][key] != value:
                        send += self.__line_update_value(player, key) + "\n\n"  # Player changed.
            else:
                send += self.__line_update_new(player) + "\n\n"    # Client doesn't know about the update yet.
        return send

    def __add_del_updates(self, current_attributes):
        """
        :param current_attributes: current game attributes received from self.__game.get_player_attributes().
        :return: The string to send.
        """
        updates = ""
        for index, player in list(enumerate(self.__game_state))[::-1]:  # Going over the list backwards so that when
            if player not in current_attributes:  # the client deletes more than 1 player at a time there are no bugs.
                updates += self.__line_update_del(player, index) + "\n\n"  # Client doesn't know player disconnected.
        return updates

    def __line_update_value(self, player, attribute):
        """Returns a line that updates one of the player's attributes as should be sent to the client."""
        value = pickle.dumps(getattr(player.hero, attribute), pickle.HIGHEST_PROTOCOL)
        return "%s~%s~%s~%s~%s" % ("UPDATE", self.get_side(player), str(player.get_index()), attribute, value)

    def __line_update_new(self, player):
        """Returns a line that adds a new player to the player's game as should be sent to the client."""
        return "%s~%s~%s" % ("ADD", self.get_side(player), pickle.dumps(player.hero, pickle.HIGHEST_PROTOCOL))

    def __line_update_del(self, player, index):
        """Returns a line that deletes a player from the player's match as should be sent to the client."""
        return "%s~%s~%s" % ("REMOVE", self.get_side(player), str(index))

    def get_side(self, player):
        """Returns whether the player is in the dame team as self or not."""
        if self.__team == player.get_team():
            return "ALLIES"
        return "ENEMIES"

    def get_index(self):
        """Returns the index of the player in his team's list of players."""
        if self.__team == Game.red_team:
            return self.__game.get_index_red(self)
        elif self.__team == Game.blue_team:
            return self.__game.get_index_blue(self)

    def get_attribute_dict(self):
        attr_dict = vars(self.__hero)
        return attr_dict

    def remove(self):
        """
        Removes the player from the game he is in. Stops the communication with the client.
        It is unrecommended to keep using a removed Player object, and can cause bugs.
        You will not, in any way, be able to communicate with the client or
        access the game the player was previously part of.
        :return: None.
        """
        self.__recv = False
        self.__send = False
        try:
            self.__game.remove(self)
        except AttributeError:
            return    # Another thread has already removed this object.
        self.__game = None
        self.__sock = None
        print(str(self.sock_name) + " Disconnected")

    def kill(self, msg):
        """This function should be called when the player was killed
        or needs to be taken out of the for any other reason.
        'msg' will be displayed to the player."""
        self._send_by_size("PLAYER KICKED~%s" % msg, 32)
        self.remove()

    def _updatex(self, newx):
        """Returns value of hero's x based on newx and limits of map."""
        if newx > self._upperx:
            return self._upperx
        elif newx < self._lowerx:
            return self._lowerx
        else:
            return newx

    def _updatey(self, newy):
        """Returns value of hero's y based on newy. and limits of map."""
        if newy > self._uppery:
            return self._uppery
        elif newy < self._lowery:
            return self._lowery
        else:
            return newy

    def _fix_diagonal_movement(self, newx, newy):
        """
        Fixes newx, newy so hero won't move too fast when moving diagonally.
        ASSUMES IT IS NEEDED FOR IT TO BE CALLED.
        :param newx: new character x after checking keys, before updating self.__hero.
        :param newy: new character y after checking keys, before updating self.__hero.
        :return: newx, newy.
        """
        return self.__hero.rect.centerx + ((newx - self.__hero.rect.centerx) / math.sqrt(2)),\
            self.__hero.rect.centery + ((newy - self.__hero.rect.centery) / math.sqrt(2))

    @staticmethod
    def get_player_object(game, sock, character_side):
        """
        Get the info needed to create a game object from the client's socket.
        Works with the send_basic_data method on the client side.
        :param game: The game the client is part of.
        :param sock: The socket used to communicate with the client.
        :param character_side: determines whether the server decides about
        the Character object's attributes or the client.
        Use Player.server_character and Player.client_character to choose.
        :return: A Player object that represents the client, or None if a connection could not be made.
        """
        try:
            client = Player(game, sock, None, None, 0, (0, 0))  # dummy
            hero = client.__get_hero(character_side)
            client._send("TEAM?")
            team = client._recv_by_size(32)
            # hero.update_character_image(team)    # Receives character with no image.
            client._send("FPS?")
            fps = int(client._recv_by_size(32))
            client._send("RESOLUTION WIDTH")
            resolution_x = int(client._recv_by_size(32))
            client._send("RESOLUTION HEIGHT")
            resolution_y = int(client._recv_by_size(32))
            client._send("OK END")
            client.__info_for_client(hero, character_side)
        except (socket.error, TypeError):
            could_not_connect(sock)
            return None
        try:
            return Player(game, sock, hero, team, fps, (resolution_x, resolution_y))
        except (ValueError, TypeError):
            could_not_connect(sock)
            return None

    def __get_hero(self, character_side):
        if character_side == Player.client_character:
            self._send("CHARACTER?")
            return pickle.loads(self._recv_by_size(32))
        else:
            with open(Player.object_file, 'r+') as f:
                return pickle.load(f)

    def __info_for_client(self, hero, character_side):
        """Part of the Game.get_player_object method that sends data to the client."""
        if self._recv(8) == "MAP NAME":
            self._send_by_size(self.get_map_name(), 32)
        else:
            raise socket.error

        if character_side == Player.server_character:
            if self._recv(9) == "CHARACTER":
                self._send_by_size(pickle.dumps(hero), 32)
            else:
                raise socket.error

        # if self._recv(16) == "INACTIVE TIMEOUT":
        #     self._send_by_size(str(Game.inactive_time_kick), 32)
        # else:
        #     raise socket.error


def could_not_connect(sock):
    print("Could not connect: " + sock.getsockname()[0])


def debug_print(*s):
    """Prints only when global DEBUG is set to True."""
    if DEBUG:
        print_lock.acquire()
        print("".join(str(word) for word in s))
        print_lock.release()
