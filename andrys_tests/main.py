class SortStrategy:
    def sort(self, data: list) -> list:
        raise NotImplementedError("Subclasses should implement this!")

class AscendingSort(SortStrategy):
    def sort(self, data: list) -> list:
        return sorted(data)
    
class DescendingSort(SortStrategy):
    def sort(self, data: list) -> list:
        return sorted(data, reverse=True)
    
class AbsoluteSort(SortStrategy):
    def sort(self, data: list) -> list:
        return sorted(data, key=abs) 
    
class Sorter:
    def __init__(self, strategy: SortStrategy) -> None:
        self._strategy = strategy
        
    @property
    def strategy(self) -> SortStrategy:
        return self._strategy
    
    @strategy.setter
    def strategy(self, strategy: SortStrategy) -> None:
        self._strategy = strategy
        
    def sort(self, data: list) -> list:
        return self._strategy.sort(data)
    
data = [3, -1, 2, -7, 5]

sorter = Sorter(AscendingSort())
print(sorter.sort(data))  # [-7, -1, 2, 3, 5]

sorter.strategy = DescendingSort()
print(sorter.sort(data))  # [5, 3, 2, -1, -7]

sorter.strategy = AbsoluteSort()
print(sorter.sort(data))  # [-1, 2, 3, 5, -7]


    
    