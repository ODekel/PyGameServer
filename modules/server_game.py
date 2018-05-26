import math
import socket
from threading import Thread
from sys import exit as sysexit
from os import path
from PIL import Image
import time
import pickle
import copy
import pygame
import imp
character = imp.load_source("character", "modules\\character.py")

DEBUG = True


class Game(object):
    """Represents an object used to store data and help control a game."""
    red_team = "RED"
    blue_team = "BLUE"

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
        self.__ip = ip
        self.__socket = socket.socket()
        self._connection_port = connection_port
        self._game_port = game_port
        self.max_players = max_players
        self.__listen = False
        self.__match = False
        self.timeout = None
        self.__game_map_name = game_map
        self.__game_map_size = Image.open(game_map).size
        self.__spawn_loc = spawn_loc
        self.__red_team = []
        self.__blue_team = []

    def get_state(self):
        """
        :return: A list with all player objects in game.
        """
        return copy.copy(self.__red_team + self.__blue_team)

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

    def listen(self):
        """Lets players connect to the server using the connection_port and game_port.
        Will not accept more players than max_players to the server."""
        self.__socket.bind((self.__ip, self._connection_port))
        self.__socket.listen(self.max_players)
        self.__listen = True
        while self.__listen:
            if not self.is_full():
                client_socket, client_addr = self.__socket.accept()
                print("Trying to connect: " + str(client_addr[0]))
                player = Thread(target=self.handle_client, args=(client_socket, self._connection_port))
                player.start()
            else:
                client_socket, client_address = sock.accept()
                client_socket.sendall("SERVER IS FULL")
                client_socket.close()
        self.__socket.close()
        self.__socket = socket.socket()

    def stop_listening(self):
        """Stop accepting new clients using connection_port. Stops the listen method."""
        self.__listen = False

    def is_full(self):
        """
        :return: True when the amount of connected players equals to max_players, False otherwise.
        """
        return True if len(self.__red_team) + len(self.__blue_team) >= self.max_players != 0 else False

    def handle_client(self, client_socket, port):
        """Starts the communication between a single client and the server."""
        # Game.connect_to_client(client_socket, port, self.timeout)
        # client_socket.close()
        # client_socket = socket.socket()
        # client_socket.connect((client_addr[0], port))
        # sock.bind((self.__ip, port))
        # sock.listen(1)
        # client_socket, client_address = sock.accept()
        if Game.connect_to_client(client_socket, port, self.timeout) is None:
            return None
        player = Player.get_player_object(self, client_socket)
        self.__add_to_game(player)
        print("Connected: " + str(client_socket.getsockname()[0]))
        self.__call_init_player_client(player)
        sender = Thread(target=player.send_loop)
        receiver = Thread(target=player.recv_loop)
        sender.start()
        receiver.start()
        sender.join()
        receiver.join()
        self.remove(player)

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
        self.__game_state = self.__game.get_state()
        self.__locations = {}
        for player in self.__game_state:
            self.__locations[player] = player.get_location()
        self.sock_name = str(sock.getsockname()[0])

    @property
    def hero(self):
        return self.__hero

    def init_player_client(self, allies, enemies):
        """Must be called after adding the player object to the game (That was given to the constructor).
        allies and enemies are lists of players.
        Returns None."""
        picklable_allies = [player.hero for player in allies]
        picklable_enemies = [player.hero for player in enemies]
        self._send("ALLIES")
        self._send_by_size(pickle.dumps(picklable_allies), 32)
        self._send("ENEMIES")
        self._send_by_size(pickle.dumps(picklable_enemies), 32)
        self._send("HERO POS")
        self._send_by_size(str(allies.index(self)), 32)

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
        Receive by size a string from the client. If first message is not an int, will return it.
        :param header_size: The size (in bytes) of the header.
        :return: The string received.
        """
        sizestr = self.__sock.recv(header_size)
        try:
            size = int(sizestr)
        except ValueError:
            return sizestr
        return self.__sock.recv(size)

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

    def handle_player_data(self, pressed):
        """
        Applies data to the game the player is part of, once.
        pressed is a pygame.key.pressed object.
        Compatible with receive_player_data method.
        :return: None.
        """
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
        if newx != self.__hero.rect.centerx and newy != self.__hero.rect.centery:
            newx, newy = self._fix_diagonal_movement(newx, newy)
        self.__hero.rect.center = (self._updatex(newx), self._updatey(newy))

    def recv_loop(self):
        """
        Will run until stopped, receiving data from the player and updating attributes accordingly.
        When stopped by the server or the client, will delete the player from the game.
        :return: None.
        """
        self.__recv = True
        cnt = 0
        while self.__recv:
            try:
                data = self.receive_player_data()
            except socket.error:
                break
            if data == "" or data == "DISCONNECT":
                break
            debug_print("recv: %s - %s" % (cnt, self.sock_name))
            self.handle_player_data(data)
            cnt += 1
            pygame.time.Clock().tick(self.__fps)
        self.__recv = False
        self.remove()

    def send_loop(self):
        """
        Will run until stopped, sending data to the player.
        When stopped by the server or the client, will delete the player from the game.
        :return: None.
        """
        self.__send = True
        cnt = 0
        snd_cnt = 0
        while self.__send:
            current_state = self.__game.get_state()
            send = self.__add_send_updates(current_state)
            try:
                if send != "":
                    self._send_by_size(send, 32)
                    debug_print("sent: %s(%s) - %s" % (cnt, snd_cnt, self.sock_name))
                    snd_cnt += 1
            except socket.error:
                break
            self.__update_game_state(current_state)
            cnt += 1
            pygame.time.Clock().tick(self.__fps)
        self.__send = False
        self.remove()

    def __update_game_state(self, current_state):
        """Updates self.__game_state and self.__locations.
        current_state is self.__game.get_state used in last loop."""
        self.__game_state = current_state
        for player in self.__game_state:
            self.__locations[player] = player.get_location()

    def __add_send_updates(self, current_state):
        """
        Returns a string to send to the client,
        according to a protocol and the changes between current_state and self.__game_state.
        :param current_state: The current state of the game.
        :return: The string to send to the client for updates.
        """
        send = ""
        for player in current_state:
            if player in self.__game_state:
                if player.get_location() != self.__locations[player]:
                    send += self.__line_update_location(player) + "\n\n"
            else:
                send += self.__line_update_new(player) + "\n\n"
        for index, player in enumerate(self.__game_state):
            if player not in current_state:
                send += self.__line_update_del(player, index) + "\n\n"
        return send

    def __line_update_location(self, player):
        """Returns a line of updating a player's location as should be sent to the client."""
        loc = pickle.dumps(player.get_location())
        if self == player:
            return "HERO~" + loc
        elif self.__team == player.get_team():
            side = "ALLIES"
        else:
            side = "ENEMIES"
        if self.__team == Game.red_team:
            return "%s~%s~%s" % (side, str(self.__game.get_index_red(player)), loc)
        elif self.__team == Game.blue_team:
            return "%s~%s~%s" % (side, str(self.__game.get_index_blue(player)), loc)

    def __line_update_new(self, player):
        """Returns a line of adding a new player to the player's game as should be sent to the client."""
        if self.__team == player.get_team():
            side = "ALLIES"
        else:
            side = "ENEMIES"
        return "%s~ADD~%s" % (side, pickle.dumps(player.hero))

    def __line_update_del(self, player, index):
        """Returns a line of deleting a player from the player's match as should be sent to the client."""
        if self.__team == player.get_team():
            side = "ALLIES"
        else:
            side = "ENEMIES"
        if self.__team == Game.red_team:
            return "%s~%s~%s" % (side, str(index), "REMOVE")
        elif self.__team == Game.blue_team:
            return "%s~%s~%s" % (side, str(index), "REMOVE")

    def remove(self):
        """
        Removes the player from the game he is in. Stops the communication with the client.
        It is unrecommended to keep using a removed Player object, and can cause bugs.
        You will not, in any way, be able to communicate with the client or
        access the game the player was previously part of.
        :return: None.
        """
        if self.__sock is None:    # Another thread already removed this object.
            return
        print(str(self.sock_name) + " Disconnected")
        self.__recv = False
        self.__send = False
        self.__game.remove(self)
        self.__game = None
        self.__sock = None

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
    def get_player_object(game, sock):
        """
        Get the info needed to create a game object from the client's socket.
        Works with the send_basic_data method on the client side.
        :param game: The game the client is part of.
        :param sock: The socket used to communicate with the client.
        :return: A Player object that represents the client, or None if a connection could not be made.
        """
        try:
            client = Player(game, sock, None, None, 0, (0, 0))
            client._send("CHARACTER?")
            hero = pickle.loads(client._recv_by_size(32))
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
            if client._recv(8) == "MAP NAME":
                client._send_by_size(client.get_map_name(), 32)
            else:
                raise socket.error
        except (socket.error, TypeError):
            could_not_connect(sock)
            return None
        try:
            return Player(game, sock, hero, team, fps, (resolution_x, resolution_y))
        except (ValueError, TypeError):
            could_not_connect(sock)
            return None


def could_not_connect(sock):
    print("Could not connect: " + sock.getsockname()[0])


def debug_print(*s):
    """Prints only when global DEBUG is set to True."""
    if DEBUG:
        print("".join(str(word) for word in s))
