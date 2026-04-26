import React, { useEffect, useRef } from 'react';
import { Box } from 'ink';

/**
 * A container component that efficiently renders only visible messages
 * Uses a fixed window approach rather than a full virtualization library
 */
export const FixedWindowScroller = React.memo(({
  items,
  height,
  width,
  itemHeight = 3, // Average height of each item in terminal rows
  renderItem,
  overscrollItems = 20, // Number of items to render outside visible area
  onScroll,
  initialScrollToEnd = true,
}) => {
  const containerRef = useRef(null);
  const lastScrollTopRef = useRef(0);
  const lastItemsLengthRef = useRef(items.length);
  
  // Calculate visible window based on container dimensions
  const [visibleWindow, setVisibleWindow] = React.useState({
    startIndex: Math.max(0, items.length - Math.floor(height / itemHeight) - overscrollItems),
    endIndex: items.length,
    scrollTop: 0
  });
  
  // Handle scroll events
  const handleScroll = React.useCallback((event) => {
    if (!containerRef.current) return;
    
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const scrollTopDiff = Math.abs(scrollTop - lastScrollTopRef.current);
    
    // Only update if we've scrolled a significant amount
    if (scrollTopDiff > (itemHeight / 2)) {
      const totalItems = items.length;
      const visibleItems = Math.floor(clientHeight / itemHeight);
      
      // Calculate the first visible item index
      const firstVisibleItemIndex = Math.floor(scrollTop / itemHeight);
      
      // Calculate start and end indices with overscroll
      const startIndex = Math.max(0, firstVisibleItemIndex - overscrollItems);
      const endIndex = Math.min(
        totalItems, 
        firstVisibleItemIndex + visibleItems + overscrollItems
      );
      
      setVisibleWindow({ startIndex, endIndex, scrollTop });
      lastScrollTopRef.current = scrollTop;
      
      // Call external scroll handler if provided
      if (onScroll) {
        onScroll({
          scrollTop,
          scrollHeight,
          clientHeight,
          firstVisibleItemIndex,
          lastVisibleItemIndex: firstVisibleItemIndex + visibleItems,
          isAtTop: scrollTop < itemHeight,
          isAtBottom: scrollTop + clientHeight >= scrollHeight - itemHeight
        });
      }
    }
  }, [items.length, itemHeight, overscrollItems, onScroll]);
  
  // Auto-scroll to bottom when new items are added
  useEffect(() => {
    if (!containerRef.current) return;
    
    const isNewMessagesAdded = items.length > lastItemsLengthRef.current;
    const isNearBottom = containerRef.current.scrollHeight - containerRef.current.clientHeight - containerRef.current.scrollTop < itemHeight * 3;
    
    if ((isNewMessagesAdded && isNearBottom) || initialScrollToEnd) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
      
      // Update the visible window to show the end
      setVisibleWindow({
        startIndex: Math.max(0, items.length - Math.floor(height / itemHeight) - overscrollItems),
        endIndex: items.length,
        scrollTop: containerRef.current.scrollHeight
      });
    }
    
    lastItemsLengthRef.current = items.length;
  }, [items.length, height, itemHeight, overscrollItems, initialScrollToEnd]);
  
  // Get the visible subset of items
  const visibleItems = items.slice(visibleWindow.startIndex, visibleWindow.endIndex);
  
  return (
    <Box
      ref={containerRef}
      overflow="auto"
      width={width}
      height={height}
      onScroll={handleScroll}
      style={{ scrollbarGutter: 'stable' }}
    >
      {/* Top spacer */}
      {visibleWindow.startIndex > 0 && (
        <Box
          width="100%"
          height={visibleWindow.startIndex * itemHeight}
          padding={0}
        />
      )}
      
      {/* Visible items */}
      {visibleItems.map((item, index) => 
        renderItem({
          item,
          index: visibleWindow.startIndex + index,
          isVisible: true
        })
      )}
      
      {/* Bottom spacer */}
      {visibleWindow.endIndex < items.length && (
        <Box
          width="100%"
          height={(items.length - visibleWindow.endIndex) * itemHeight}
          padding={0}
        />
      )}
    </Box>
  );
});

export default FixedWindowScroller;