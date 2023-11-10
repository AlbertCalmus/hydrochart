class Store:
    def __init__(self):
        self.data = {}
        self.normalized = None

    def clear(self):
        self.data = {}
        self.normalized = None
