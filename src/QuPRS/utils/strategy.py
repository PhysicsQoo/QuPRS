import multiprocessing
import os
import pickle
import resource
import tempfile
from abc import ABC, abstractmethod

import psutil

from QuPRS.interface.load_qiskit import add_gate
from QuPRS.pathsum import PathSum


class Strategy(ABC):
    _registry: dict = {}

    def __init__(self):
        self.count: int = 0

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "name"):
            cls._registry[cls.name] = cls
        else:
            print(
                f"Warning: Class {cls.__name__} does not define "
                "a 'name' attribute and cannot be registered."
            )

    @classmethod
    def get(cls, name: str) -> "Strategy":
        """
        Factory method: Look up the registry by name and return an instance of
                        the strategy.
        """
        strategy_class = cls._registry.get(name.lower())
        if not strategy_class:
            raise ValueError(
                f"Unknown strategy: '{name}'."
                f"Available strategies: {list(cls._registry.keys())}"
            )
        return strategy_class()

    @abstractmethod
    def run(self, pathsum_circuit: "PathSum", gates1: list, gates2: list) -> "PathSum":
        """
        Run the strategy to process the given circuits.
        """
        raise NotImplementedError

    @staticmethod
    def _set_memory_limit(limit_ratio=0.85):
        """
        Set a memory limit for the current process.
        """
        try:
            total_mem = psutil.virtual_memory().total
            limit = int(total_mem * limit_ratio)
            resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        except Exception:
            # Ignore if not supported or insufficient permissions
            pass

    @staticmethod
    def _worker(strategy_instance, queue, pathsum_circuit, gates1, gates2):
        """
        Worker process:
        1. Set memory limit.
        2. Perform computation.
        3. Write result to a temporary file.
        4. Return metadata via queue.
        """
        temp_path = None
        try:
            Strategy._set_memory_limit(limit_ratio=0.85)
            result_circuit = strategy_instance.run(pathsum_circuit, gates1, gates2)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pkl") as f:
                pickle.dump(result_circuit, f)
                temp_path = f.name
            queue.put(("success", temp_path, strategy_instance.count))
        except MemoryError:
            queue.put(("memory_error", None, None))
        except Exception as e:
            queue.put(("error", e, None))
        finally:
            del pathsum_circuit
            del gates1
            del gates2

    def safe_run(
        self, pathsum_circuit: "PathSum", gates1: list, gates2: list, timeout: int
    ) -> "PathSum":
        """
        Executes the run() method in a separate process using file-based IPC.
        """
        ctx = multiprocessing.get_context("spawn")

        queue = ctx.Queue()
        p = ctx.Process(
            target=self._worker, args=(self, queue, pathsum_circuit, gates1, gates2)
        )
        p.start()
        p.join(timeout=timeout)

        # Handle timeout
        if p.is_alive():
            p.terminate()
            p.join()
            raise TimeoutError("Strategy execution timed out.")

        # Handle crashes
        if p.exitcode != 0:
            raise MemoryError(
                f"Subprocess crashed (Exit code: {p.exitcode}). Likely out of memory."
            )

        # Handle no data returned
        if queue.empty():
            raise MemoryError("Subprocess finished but returned no data.")

        # Process result
        status, data, returned_count = queue.get()

        if status == "memory_error":
            raise MemoryError("Worker reported MemoryError.")
        if status == "error":
            raise data  # Re-raise exception from worker

        # Load result from temporary file
        temp_path = data
        result_circuit = None
        try:
            with open(temp_path, "rb") as f:
                result_circuit = pickle.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load result from temp file: {e}")
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

        self.count = returned_count
        return result_circuit


class ProportionalStrategy(Strategy):
    name = "proportional"

    def run(self, pathsum_circuit: "PathSum", gates1: list, gates2: list):
        """
        Run the proportional strategy to process the given circuits.
        """
        l1 = len(gates1)
        l2 = len(gates2)
        min_length = min(l1, l2)
        d = l1 - l2
        r = int(l1 / l2) if d > 0 else int(l2 / l1)

        if r == 1:
            for i in range(min_length):
                gate1 = gates1[i]
                gate2 = gates2[i]
                pathsum_circuit, self.count = add_gate(
                    pathsum_circuit, gate1, count=self.count
                )
                pathsum_circuit, self.count = add_gate(
                    pathsum_circuit, gate2, count=self.count, is_bra=True
                )

            if d > 0:
                for i in range(d):
                    gate1 = gates1[min_length + i]
                    pathsum_circuit, self.count = add_gate(
                        pathsum_circuit, gate1, count=self.count
                    )
            elif d < 0:
                for i in range(-d):
                    gate2 = gates2[min_length + i]
                    pathsum_circuit, self.count = add_gate(
                        pathsum_circuit, gate2, count=self.count, is_bra=True
                    )
        elif d > 0:
            for i in range(l2):
                for j in range(r):
                    gate1 = gates1[i * r + j]
                    pathsum_circuit, self.count = add_gate(
                        pathsum_circuit, gate1, count=self.count
                    )
                gate2 = gates2[i]
                pathsum_circuit, self.count = add_gate(
                    pathsum_circuit, gate2, count=self.count, is_bra=True
                )
            d2 = l1 - r * l2
            if d2 > 0:
                for i in range(d2):
                    gate1 = gates1[l2 * r + i]
                    pathsum_circuit, self.count = add_gate(
                        pathsum_circuit, gate1, count=self.count
                    )
        elif d < 0:
            for i in range(l1):
                for j in range(r):
                    gate2 = gates2[i * r + j]
                    pathsum_circuit, self.count = add_gate(
                        pathsum_circuit, gate2, count=self.count, is_bra=True
                    )
                gate1 = gates1[i]
                pathsum_circuit, self.count = add_gate(
                    pathsum_circuit, gate1, count=self.count
                )
            d2 = l2 - r * l1
            if d2 > 0:
                for i in range(d2):
                    gate2 = gates2[l1 * r + i]
                    pathsum_circuit, self.count = add_gate(
                        pathsum_circuit, gate2, count=self.count, is_bra=True
                    )

            pathsum_circuit = pathsum_circuit.reduction()

        return pathsum_circuit


class NaiveStrategy(Strategy):
    name = "naive"

    def run(self, pathsum_circuit: "PathSum", gates1: list, gates2: list):
        """
        Run the naive strategy to process the given circuits.
        """
        for i in range(min(len(gates1), len(gates2))):
            gate1 = gates1[i]
            gate2 = gates2[i]

            pathsum_circuit, self.count = add_gate(
                pathsum_circuit, gate1, count=self.count
            )
            pathsum_circuit, self.count = add_gate(
                pathsum_circuit, gate2, count=self.count, is_bra=True
            )
        if len(gates1) > len(gates2):
            for gate1 in gates1[len(gates2) :]:
                pathsum_circuit, self.count = add_gate(
                    pathsum_circuit, gate1, count=self.count
                )
        elif len(gates1) < len(gates2):
            for gate2 in gates2[len(gates1) :]:
                pathsum_circuit, self.count = add_gate(
                    pathsum_circuit, gate2, count=self.count, is_bra=True
                )
        pathsum_circuit = pathsum_circuit.reduction()
        return pathsum_circuit


class StraightforwardStrategy(Strategy):
    name = "straightforward"

    def run(self, pathsum_circuit: "PathSum", gates1: list, gates2: list):
        """
        Run the straightforward strategy to process the given circuits.
        """
        for gate in gates2:
            pathsum_circuit, self.count = add_gate(
                pathsum_circuit, gate, count=self.count, is_bra=True
            )
        for gate in gates1:
            pathsum_circuit, self.count = add_gate(
                pathsum_circuit, gate, count=self.count
            )
        pathsum_circuit = pathsum_circuit.reduction()
        return pathsum_circuit


class DifferenceStrategy(Strategy):
    name = "difference"

    def run(self, pathsum_circuit: "PathSum", gates1: list, gates2: list):
        """
        Run the difference strategy to process the given circuits.
        """
        import difflib

        def compare_lists_with_index(list1, list2):
            list1_str = [str(item) for item in list1]
            list2_str = [str(item) for item in list2]
            diff = list(difflib.ndiff(list1_str, list2_str))
            # Store index and its changes
            changes = []
            # Track current index
            index1 = index2 = 0
            for line in diff:
                if line.startswith("-"):
                    # Element from `list1`, marked as deleted
                    changes.append(("-", index1, list1[index1]))
                    index1 += 1
                elif line.startswith("+"):
                    # Element from `list2`, marked as added
                    changes.append(("+", index2, list2[index2]))
                    index2 += 1
                elif line.startswith(" "):
                    # Element present in both lists
                    changes.append((" ", index1, list1[index1]))
                    index1 += 1
                    index2 += 1
            return changes

        # Get the changed indices and their details
        changes = compare_lists_with_index(gates1, gates2)
        for change_type, index, value in changes:
            if change_type == "-":
                pathsum_circuit, self.count = add_gate(
                    pathsum_circuit, value, count=self.count
                )
            elif change_type == "+":
                pathsum_circuit, self.count = add_gate(
                    pathsum_circuit, value, count=self.count, is_bra=True
                )
            elif change_type == " ":
                pathsum_circuit, self.count = add_gate(
                    pathsum_circuit, value, count=self.count
                )
                pathsum_circuit, self.count = add_gate(
                    pathsum_circuit, value, count=self.count, is_bra=True
                )
        pathsum_circuit = pathsum_circuit.reduction()
        return pathsum_circuit
