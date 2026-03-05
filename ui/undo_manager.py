# ui/undo_manager.py
"""
Undo/Redo Manager using Command Pattern
Provides centralized undo/redo functionality with 500ms coalescing
"""

import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional


class Command(ABC):
    """Abstract base class for all undoable commands"""
    
    def __init__(self, name: str = "Unknown"):
        self.name = name
        self.timestamp = time.time()
        self.coalescing_group: Optional[str] = None
    
    @abstractmethod
    def execute(self):
        """Execute the command (called when initially performed)"""
        pass
    
    @abstractmethod
    def undo(self):
        """Undo the command"""
        pass
    
    @abstractmethod
    def redo(self):
        """Redo the command (usually same as execute)"""
        pass
    
    def can_coalesce_with(self, other: 'Command') -> bool:
        """Check if this command can be merged with another"""
        return False
    
    def coalesce(self, other: 'Command') -> 'Command':
        """Merge another command into this one, return merged command"""
        return self


class ValueChangeCommand(Command):
    """Command for value changes (entry fields, etc.)"""
    
    COALESCE_WINDOW = 0.5  # 500ms window for coalescing
    
    def __init__(self, widget_ref, old_value: Any, new_value: Any, 
                 setter_callback: Callable, name: str = "Value Change"):
        super().__init__(name)
        self.widget_ref = widget_ref  # Weak reference to widget
        self.old_value = old_value
        self.new_value = new_value
        self.setter_callback = setter_callback
        self.coalescing_group = f"value_{id(widget_ref)}"
    
    def execute(self):
        # Already done by user, just record it
        pass
    
    def undo(self):
        self.setter_callback(self.old_value)
    
    def redo(self):
        self.setter_callback(self.new_value)
    
    def can_coalesce_with(self, other: 'Command') -> bool:
        """Check if commands can be merged (same widget, within time window)"""
        if not isinstance(other, ValueChangeCommand):
            return False
        if self.coalescing_group != other.coalescing_group:
            return False
        time_diff = abs(self.timestamp - other.timestamp)
        return time_diff < self.COALESCE_WINDOW
    
    def coalesce(self, other: 'ValueChangeCommand') -> 'ValueChangeCommand':
        """Merge another command, keeping original old_value but updating new_value"""
        self.new_value = other.new_value
        self.timestamp = other.timestamp
        return self
    
    def __repr__(self):
        return f"ValueChangeCommand({self.name}: {self.old_value!r} -> {self.new_value!r})"


class SelectionCommand(Command):
    """Command for selection changes (combobox, etc.)"""
    
    def __init__(self, widget_ref, old_selection: Any, new_selection: Any,
                 setter_callback: Callable, name: str = "Selection Change"):
        super().__init__(name)
        self.widget_ref = widget_ref
        self.old_selection = old_selection
        self.new_selection = new_selection
        self.setter_callback = setter_callback
    
    def execute(self):
        pass
    
    def undo(self):
        self.setter_callback(self.old_selection)
    
    def redo(self):
        self.setter_callback(self.new_selection)
    
    def __repr__(self):
        return f"SelectionCommand({self.name}: {self.old_selection!r} -> {self.new_selection!r})"


class ToggleCommand(Command):
    """Command for toggle/checkbox changes"""
    
    def __init__(self, widget_ref, old_state: bool, new_state: bool,
                 setter_callback: Callable, name: str = "Toggle Change"):
        super().__init__(name)
        self.widget_ref = widget_ref
        self.old_state = old_state
        self.new_state = new_state
        self.setter_callback = setter_callback
    
    def execute(self):
        pass
    
    def undo(self):
        self.setter_callback(self.old_state)
    
    def redo(self):
        self.setter_callback(self.new_state)
    
    def __repr__(self):
        return f"ToggleCommand({self.name}: {self.old_state} -> {self.new_state})"


class CompoundCommand(Command):
    """Command that groups multiple commands together"""
    
    def __init__(self, commands: list, name: str = "Compound Action"):
        super().__init__(name)
        self.commands = commands
    
    def execute(self):
        for cmd in self.commands:
            cmd.execute()
    
    def undo(self):
        # Undo in reverse order
        for cmd in reversed(self.commands):
            cmd.undo()
    
    def redo(self):
        for cmd in self.commands:
            cmd.redo()
    
    def __repr__(self):
        return f"CompoundCommand({self.name}, {len(self.commands)} commands)"


class UndoManager:
    """
    Centralized undo/redo manager using Command Pattern
    """
    
    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.history: list[Command] = []
        self.position: int = -1  # Current position in history
        self._in_undo_redo = False  # Flag to prevent recording during undo/redo
        self._coalesce_timer = None
    
    def execute(self, command: Command):
        """Execute a new command and add to history"""
        # Don't record commands during undo/redo operations
        if self._in_undo_redo:
            return
        
        # Check if we can coalesce with the last command
        if self.position >= 0 and command.can_coalesce_with(self.history[self.position]):
            # Merge into last command
            merged = self.history[self.position].coalesce(command)
            self.history[self.position] = merged
            return
        
        # Remove any redo history if we're not at the end
        if self.position < len(self.history) - 1:
            self.history = self.history[:self.position + 1]
        
        # Add new command
        self.history.append(command)
        self.position += 1
        
        # Enforce max history
        if len(self.history) > self.max_history:
            self.history.pop(0)
            self.position -= 1
        
        command.execute()
    
    def can_undo(self) -> bool:
        """Check if undo is possible"""
        return self.position >= 0
    
    def can_redo(self) -> bool:
        """Check if redo is possible"""
        return self.position < len(self.history) - 1
    
    def undo(self) -> Optional[str]:
        """Undo the last command, returns command description"""
        if not self.can_undo():
            return None
        
        self._in_undo_redo = True
        try:
            command = self.history[self.position]
            command.undo()
            self.position -= 1
            return f"Undo: {command.name}"
        finally:
            self._in_undo_redo = False
    
    def redo(self) -> Optional[str]:
        """Redo the next command, returns command description"""
        if not self.can_redo():
            return None
        
        self._in_undo_redo = True
        try:
            self.position += 1
            command = self.history[self.position]
            command.redo()
            return f"Redo: {command.name}"
        finally:
            self._in_undo_redo = False
    
    def clear(self):
        """Clear all history"""
        self.history.clear()
        self.position = -1
    
    def get_history_summary(self) -> list[str]:
        """Get a summary of history for debugging"""
        summary = []
        for i, cmd in enumerate(self.history):
            marker = " <--" if i == self.position else ""
            summary.append(f"  [{i}] {cmd}{marker}")
        return summary
