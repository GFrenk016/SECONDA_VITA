from typing import Callable, List

class Hooks:
    def __init__(self):
        self._on_tick: List[Callable] = []
        self._on_command: List[Callable] = []
        
    def on_tick(self, fn: Callable):
        self._on_tick.append(fn)
        return fn
    
    def on_command(self, fn: Callable):
        self._on_command.append(fn)
        return fn
    
    # Dispatchers
    def dispatch_tick(self, ctx):
        for fn in self._on_tick:
            fn(ctx)
        
    def dispatch_command(self, ctx, raw: str):
        for fn in self._on_command:
            fn(ctx, raw)