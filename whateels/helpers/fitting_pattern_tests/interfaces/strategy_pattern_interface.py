from abc import ABC, abstractmethod

class StrategyPatternInterface(ABC):
    @abstractmethod
    def fit(self, data):
        # Implement fitting logic in subclasses
        pass