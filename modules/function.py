class GameFunction(object):
    """This class represent the game_func in the server_game Game class."""
    def __init__(self, func, *args):
        """Create a new GameFunction function."""
        self.func = func
        self.args = args

    def __call__(self):
        """Called to run self.func."""
        self.func(*self.args)
