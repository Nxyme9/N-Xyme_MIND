"""Focus manager - Ported from ant-source-code Ink.

This module provides DOM-like focus management equivalent to Ink's FocusManager class,
adapted for use with the Textual framework.

Usage:
    from tui.hooks import FocusManager, FocusEvent
    
    # Create focus manager
    fm = FocusManager(on_focus_event)
    fm.focus(button_element)
    fm.focus_next()
    fm.focus_previous()
"""

from typing import Callable, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


# Constants
MAX_FOCUS_STACK = 32


class FocusEventType(Enum):
    """Focus event types."""
    FOCUS = "focus"
    BLUR = "blur"


@dataclass
class FocusEvent:
    """Focus event.
    
    Attributes:
        type: The type of focus event (focus or blur)
        target: The element that was focused/blurred
        relatedTarget: The related element (e.g., for blur, the element losing focus;
                    for focus, the element that had focus before)
    """
    type: FocusEventType
    target: Any = None
    relatedTarget: Any = None


# Focus handler type
FocusDispatch = Callable[[Any, FocusEvent], bool]


@dataclass
class FocusableElement:
    """A focusable element in the TUI.
    
    This represents a widget that can receive focus.
    
    Attributes:
        id: Unique identifier for the element
        widget: The actual widget (Textual widget)
        tab_index: Tab order index (None for default, -1 to skip)
        data: Optional custom data associated with element
    """
    id: str
    widget: Any = None
    tab_index: Optional[int] = None
    data: dict = field(default_factory=dict)
    
    def __hash__(self) -> int:
        return hash(self.id)


class FocusManager:
    """DOM-like focus manager for the N-Xyme TUI.
    
    Pure state - tracks activeElement and a focus stack. Has no reference
    to the tree; callers pass the root when tree walks are needed.
    
    Attributes:
        active_element: The currently focused element, or None
    """
    
    def __init__(self, dispatch_focus_event: FocusDispatch) -> None:
        """Initialize the focus manager.
        
        Args:
            dispatch_focus_event: Callback for handling focus events
        """
        self._dispatch = dispatch_focus_event
        self.active_element: Optional[FocusableElement] = None
        self._enabled = True
        self._focus_stack: list[FocusableElement] = []
    
    def focus(self, element: FocusableElement) -> None:
        """Focus a specific element.
        
        Args:
            element: The element to focus
        """
        if element == self.active_element:
            return
        if not self._enabled:
            return
        
        previous = self.active_element
        if previous:
            # Deduplicate before pushing to prevent unbounded growth
            if previous in self._focus_stack:
                self._focus_stack.remove(previous)
            self._focus_stack.append(previous)
            if len(self._focus_stack) > MAX_FOCUS_STACK:
                self._focus_stack.pop(0)
            self._dispatch(previous, FocusEvent(FocusEventType.BLUR, previous, element))
        
        self.active_element = element
        self._dispatch(element, FocusEvent(FocusEventType.FOCUS, element, previous))
    
    def blur(self) -> None:
        """Remove focus from the currently focused element."""
        if not self.active_element:
            return
        
        previous = self.active_element
        self.active_element = None
        self._dispatch(previous, FocusEvent(FocusEventType.BLUR, previous, None))
    
    def handle_node_removed(
        self,
        element: FocusableElement,
        root: Optional[FocusableElement] = None,
    ) -> None:
        """Handle an element being removed from the tree.
        
        Handles both the exact node and any focused descendant within
        the removed subtree. Dispatches blur and restores focus from stack.
        
        Args:
            element: The element being removed
            root: The root element for tree checks (optional)
        """
        # Remove element from stack
        if element in self._focus_stack:
            self._focus_stack.remove(element)
        
        # Check if active_element is the removed element OR a descendant
        if not self.active_element:
            return
        
        if self.active_element != element:
            # Check if we can verify tree relationship
            if root and not self._is_in_tree(self.active_element, root):
                pass  # Might be descendant, safe to keep focus
            else:
                return
        
        removed = self.active_element
        self.active_element = None
        self._dispatch(removed, FocusEvent(FocusEventType.BLUR, removed, None))
        
        # Restore focus to the most recent still-mounted element
        while self._focus_stack:
            candidate = self._focus_stack.pop()
            if not root or self._is_in_tree(candidate, root):
                self.active_element = candidate
                self._dispatch(candidate, FocusEvent(FocusEventType.FOCUS, candidate, removed))
                return
    
    def handle_auto_focus(self, element: FocusableElement) -> None:
        """Handle autoFocus attribute - focus element on mount.
        
        Args:
            element: The element to auto-focus
        """
        self.focus(element)
    
    def handle_click_focus(self, element: FocusableElement) -> None:
        """Handle click to focus - focus element on click if it has tabIndex.
        
        Args:
            element: The clicked element
        """
        if element.tab_index is not None:
            self.focus(element)
    
    def enable(self) -> None:
        """Enable focus management."""
        self._enabled = True
    
    def disable(self) -> None:
        """Disable focus management."""
        self._enabled = False
    
    def focus_next(self, elements: list[FocusableElement]) -> None:
        """Move focus to the next tabbable element.
        
        Args:
            elements: List of all focusable elements in DOM order
        """
        self._move_focus(1, elements)
    
    def focus_previous(self, elements: list[FocusableElement]) -> None:
        """Move focus to the previous tabbable element.
        
        Args:
            elements: List of all focusable elements in DOM order
        """
        self._move_focus(-1, elements)
    
    def _move_focus(self, direction: int, elements: list[FocusableElement]) -> None:
        """Move focus in the given direction.
        
        Args:
            direction: 1 for next, -1 for previous
            elements: List of all focusable elements
        """
        if not self._enabled:
            return
        
        tabbable = self._collect_tabbable(elements)
        if not tabbable:
            return
        
        current_index = (
            tabbable.index(self.active_element)
            if self.active_element in tabbable
            else -1
        )
        
        next_index = (
            0 if direction == 1
            else len(tabbable) - 1
        ) if current_index == -1 else (
            current_index + direction + len(tabbable)
        ) % len(tabbable)
        
        next_element = tabbable[next_index]
        if next_element:
            self.focus(next_element)
    
    def _collect_tabbable(self, elements: list[FocusableElement]) -> list[FocusableElement]:
        """Collect all tabbable elements.
        
        Args:
            elements: List of all elements to check
            
        Returns:
            List of elements with tab_index >= 0
        """
        # Filter to elements with tab_index >= 0, sort by tab_index
        tabbable = [
            el for el in elements
            if el.tab_index is not None and el.tab_index >= 0
        ]
        tabbable.sort(key=lambda el: el.tab_index or 0)
        return tabbable
    
    def _is_in_tree(self, element: FocusableElement, root: FocusableElement) -> bool:
        """Check if element is in the tree rooted at root.
        
        Args:
            element: Element to check
            root: Root element
            
        Returns:
            True if element is descendant of root
        """
        # Simple check - this is a simplified version
        # In a real implementation, we'd walk the widget tree
        return True  # Placeholder - actual implementation depends on widget structure
    
    @property
    def is_enabled(self) -> bool:
        """Check if focus is enabled."""
        return self._enabled
    
    @property
    def has_focus(self) -> bool:
        """Check if any element currently has focus."""
        return self.active_element is not None
    
    @property
    def focus_stack_depth(self) -> int:
        """Get the current focus stack depth."""
        return len(self._focus_stack)


class FocusableMixin:
    """Mixin to add focus capabilities to TUI widgets.
    
    Usage:
        class MyButton(FocusableMixin, Widget):
            def __init__(self):
                super().__init__()
                self.focus_manager = FocusManager(self.on_focus_event)
                self.focusable = FocusableElement(id="my-button", tab_index=0)
    """
    
    def __init__(self) -> None:
        self._focusable_element: Optional[FocusableElement] = None
        self._focus_manager: Optional[FocusManager] = None
    
    @property
    def focusable_element(self) -> FocusableElement:
        """Get the focusable element representation."""
        if self._focusable_element is None:
            self._focusable_element = FocusableElement(
                id=getattr(self, 'id', None) or str(id(self)),
                widget=self,
            )
        return self._focusable_element
    
    @property
    def focus_manager(self) -> Optional[FocusManager]:
        """Get the focus manager."""
        return self._focus_manager
    
    @focus_manager.setter
    def focus_manager(self, fm: FocusManager) -> None:
        """Set the focus manager."""
        self._focus_manager = fm
    
    def focus(self) -> None:
        """Focus this element."""
        if self._focus_manager and self._focusable_element:
            self._focus_manager.focus(self._focusable_element)
    
    def blur(self) -> None:
        """Unfocus this element."""
        if self._focus_manager:
            self._focus_manager.blur()
    
    @property
    def has_focus(self) -> bool:
        """Check if this element has focus."""
        return (
            self._focus_manager is not None
            and self._focus_manager.active_element == self._focusable_element
        )


def get_focus_manager(element: Any) -> FocusManager:
    """Get the focus manager for an element.
    
    Walk up to root and return its FocusManager.
    Like browser's `element.ownerDocument`.
    
    Args:
        element: Any element that might have a focus manager
        
    Returns:
        The FocusManager instance
        
    Raises:
        ValueError: If no focus manager found
    """
    # Walk up the widget tree
    current: Any = element
    while current:
        if hasattr(current, 'focus_manager'):
            return current.focus_manager
        if hasattr(current, 'parent'):
            current = current.parent
        else:
            break
    
    raise ValueError("Element is not in a tree with a FocusManager")


def get_root_element(element: Any) -> Any:
    """Get the root element for an element.
    
    Walk up to root and return it.
    
    Args:
        element: Any element
        
    Returns:
        The root element
    """
    current = element
    while current:
        if hasattr(current, 'parent'):
            current = current.parent
        else:
            return current
    return element