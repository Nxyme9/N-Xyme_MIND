import { useState, useCallback, useRef } from "react";

interface FeedbackState {
  isLoading: boolean;
  isSuccess: boolean;
  isError: boolean;
  message: string;
}

export function useInstantFeedback(initialMessage = "") {
  const [state, setState] = useState<FeedbackState>({
    isLoading: false,
    isSuccess: false,
    isError: false,
    message: initialMessage,
  });
  
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const clearExistingTimeout = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  const startLoading = useCallback((message = "Loading...") => {
    clearExistingTimeout();
    setState({
      isLoading: true,
      isSuccess: false,
      isError: false,
      message,
    });
  }, [clearExistingTimeout]);

  const showSuccess = useCallback((message = "Done!", duration = 2000) => {
    clearExistingTimeout();
    setState({
      isLoading: false,
      isSuccess: true,
      isError: false,
      message,
    });
    timeoutRef.current = setTimeout(() => {
      setState((prev) => ({ ...prev, isSuccess: false, message: "" }));
    }, duration);
  }, [clearExistingTimeout]);

  const showError = useCallback((message = "Error", duration = 4000) => {
    clearExistingTimeout();
    setState({
      isLoading: false,
      isSuccess: false,
      isError: true,
      message,
    });
    timeoutRef.current = setTimeout(() => {
      setState((prev) => ({ ...prev, isError: false, message: "" }));
    }, duration);
  }, [clearExistingTimeout]);

  const reset = useCallback(() => {
    clearExistingTimeout();
    setState({
      isLoading: false,
      isSuccess: false,
      isError: false,
      message: "",
    });
  }, [clearExistingTimeout]);

  return {
    ...state,
    startLoading,
    showSuccess,
    showError,
    reset,
    isIdle: !state.isLoading && !state.isSuccess && !state.isError,
  };
}

export function useClickFeedback() {
  const [isPressed, setIsPressed] = useState(false);

  const handleMouseDown = useCallback(() => setIsPressed(true), []);
  const handleMouseUp = useCallback(() => setIsPressed(false), []);
  const handleMouseLeave = useCallback(() => setIsPressed(false), []);

  return {
    isPressed,
    handlers: {
      onMouseDown: handleMouseDown,
      onMouseUp: handleMouseUp,
      onMouseLeave: handleMouseLeave,
    },
  };
}