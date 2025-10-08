from .types import *
from .interfaces.strategy_pattern_interface import StrategyPatternInterface

class FittingFactory:
    _strategies = {
        "powerlaw": PowerLawFitting,
        "polynomial": PolynomialFitting,
        "exponential": ExponentialFitting
    }
    
    @property
    def strategies(self):
        return list(self._strategies.keys())

    @classmethod
    def get_strategy(cls, name: str) -> StrategyPatternInterface:
        try:
            name = name.lower().strip()
            return cls._strategies[name]()
        except KeyError:
            raise ValueError(f"Unknown fitting strategy. Available strategies: {cls.strategies}")