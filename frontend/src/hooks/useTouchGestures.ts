"use client";

import { useCallback, useRef, useState } from "react";

const SWIPE_THRESHOLD = 50;
const PINCH_THRESHOLD = 0.1;

/**
 * Hook for detecting swipe gestures (left/right)
 * Calls onSwipeLeft or onSwipeRight when swipe is detected
 */
export function useSwipeNavigation({
  onSwipeLeft,
  onSwipeRight,
}: {
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
}) {
  const touchStartX = useRef<number>(0);
  const touchStartY = useRef<number>(0);

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX;
    touchStartY.current = e.touches[0].clientY;
  }, []);

  const handleTouchEnd = useCallback(
    (e: React.TouchEvent) => {
      const touchEndX = e.changedTouches[0].clientX;
      const touchEndY = e.changedTouches[0].clientY;

      const diffX = touchEndX - touchStartX.current;
      const diffY = touchEndY - touchStartY.current;

      // Only detect horizontal swipes (ignore vertical)
      if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > SWIPE_THRESHOLD) {
        if (diffX > 0 && onSwipeRight) {
          onSwipeRight();
        } else if (diffX < 0 && onSwipeLeft) {
          onSwipeLeft();
        }
      }
    },
    [onSwipeLeft, onSwipeRight]
  );

  return {
    onTouchStart: handleTouchStart,
    onTouchEnd: handleTouchEnd,
  };
}

/**
 * Hook for detecting pinch-to-zoom gestures
 * Calls onZoom with scale factor when pinch is detected
 */
export function usePinchToZoom({
  onZoom,
}: {
  onZoom?: (scale: number) => void;
}) {
  const initialDistance = useRef<number>(0);
  const [scale, setScale] = useState(1);

  const getDistance = (touches: React.TouchList) => {
    const dx = touches[0].clientX - touches[1].clientX;
    const dy = touches[0].clientY - touches[1].clientY;
    return Math.sqrt(dx * dx + dy * dy);
  };

  const handleTouchMove = useCallback(
    (e: React.TouchEvent) => {
      if (e.touches.length !== 2) return;

      const currentDistance = getDistance(e.touches);
      
      if (initialDistance.current === 0) {
        initialDistance.current = currentDistance;
        return;
      }

      const scaleFactor = currentDistance / initialDistance.current;
      
      // Only trigger if significant zoom change
      if (Math.abs(scaleFactor - 1) > PINCH_THRESHOLD) {
        setScale(scaleFactor);
        if (onZoom) {
          onZoom(scaleFactor);
        }
        initialDistance.current = currentDistance;
      }
    },
    [onZoom]
  );

  const handleTouchEnd = useCallback(() => {
    initialDistance.current = 0;
  }, []);

  return {
    onTouchMove: handleTouchMove,
    onTouchEnd: handleTouchEnd,
    scale,
  };
}

/**
 * Minimum touch target size constant (44px as per accessibility guidelines)
 */
export const MIN_TOUCH_TARGET = 44;