import { useRef, useCallback, useState, useEffect } from 'react';

/**
 * Custom hook for performance monitoring
 * Helps track and log performance metrics for components
 */
export function usePerformanceMonitor(componentName: string, options = { 
  logToConsole: false,
  thresholdMs: 16 // 60fps threshold
}) {
  const renderCountRef = useRef(0);
  const renderTimesRef = useRef<number[]>([]);
  const lastRenderTimeRef = useRef(performance.now());
  const [metrics, setMetrics] = useState({
    averageRenderTime: 0,
    totalRenders: 0,
    slowRenders: 0
  });

  // Measure start of render cycle
  useEffect(() => {
    const startTime = performance.now();
    
    return () => {
      const endTime = performance.now();
      const renderTime = endTime - startTime;
      
      renderCountRef.current += 1;
      renderTimesRef.current.push(renderTime);
      
      // Keep only the last 100 measurements
      if (renderTimesRef.current.length > 100) {
        renderTimesRef.current.shift();
      }
      
      // Calculate average render time
      const average = renderTimesRef.current.reduce((sum, time) => sum + time, 0) / 
                      renderTimesRef.current.length;
      
      // Count slow renders
      const slowRenders = renderTimesRef.current.filter(time => time > options.thresholdMs).length;
      
      // Update metrics
      setMetrics({
        averageRenderTime: average,
        totalRenders: renderCountRef.current,
        slowRenders
      });
      
      if (options.logToConsole && renderTime > options.thresholdMs) {
        console.log(
          `[PERF] ${componentName} render: ${renderTime.toFixed(2)}ms ` +
          `(avg: ${average.toFixed(2)}ms, slow: ${slowRenders}/${renderCountRef.current})`
        );
      }
      
      lastRenderTimeRef.current = endTime;
    };
  });

  // Function to measure specific operations
  const measureOperation = useCallback((operationName: string, fn: () => void) => {
    const start = performance.now();
    fn();
    const duration = performance.now() - start;
    
    if (options.logToConsole && duration > options.thresholdMs) {
      console.log(`[PERF] ${componentName}.${operationName}: ${duration.toFixed(2)}ms`);
    }
    
    return duration;
  }, [componentName, options.logToConsole, options.thresholdMs]);

  return { 
    metrics,
    measureOperation,
    logEvent: (event: string, durationMs?: number) => {
      if (options.logToConsole) {
        const message = durationMs 
          ? `[PERF] ${componentName}.${event}: ${durationMs.toFixed(2)}ms`
          : `[PERF] ${componentName}.${event}`;
        console.log(message);
      }
    }
  };
}

/**
 * Hook to throttle scroll events and track scroll performance
 */
export function useScrollPerformance(componentName: string, options = { 
  logToConsole: false,
  sampleRate: 0.1, // Only log 10% of scroll events to reduce noise
  thresholdMs: 16
}) {
  const scrollCountRef = useRef(0);
  const scrollTimesRef = useRef<number[]>([]);
  const isScrollingRef = useRef(false);
  const scrollStartTimeRef = useRef(0);
  const scrollThrottleTimerRef = useRef<NodeJS.Timeout | null>(null);

  const onScrollStart = useCallback(() => {
    if (!isScrollingRef.current) {
      isScrollingRef.current = true;
      scrollStartTimeRef.current = performance.now();
      
      if (options.logToConsole) {
        console.log(`[SCROLL] ${componentName} scroll started`);
      }
    }
  }, [componentName, options.logToConsole]);

  const onScrollEnd = useCallback(() => {
    if (isScrollingRef.current) {
      const duration = performance.now() - scrollStartTimeRef.current;
      scrollTimesRef.current.push(duration);
      
      // Keep array at reasonable size
      if (scrollTimesRef.current.length > 50) {
        scrollTimesRef.current.shift();
      }
      
      isScrollingRef.current = false;
      
      if (options.logToConsole && Math.random() < options.sampleRate) {
        const avg = scrollTimesRef.current.reduce((sum, time) => sum + time, 0) / 
                   scrollTimesRef.current.length;
                   
        console.log(
          `[SCROLL] ${componentName} scroll ended: ${duration.toFixed(2)}ms ` +
          `(avg: ${avg.toFixed(2)}ms)`
        );
      }
    }
  }, [componentName, options.logToConsole, options.sampleRate]);

  const onScroll = useCallback(() => {
    scrollCountRef.current += 1;
    
    // Start scrolling tracking if not already
    onScrollStart();
    
    // Reset the scroll end timer
    if (scrollThrottleTimerRef.current) {
      clearTimeout(scrollThrottleTimerRef.current);
    }
    
    // Set timer to detect when scrolling stops
    scrollThrottleTimerRef.current = setTimeout(() => {
      onScrollEnd();
    }, 150); // Consider scrolling stopped after 150ms of inactivity
    
  }, [onScrollStart, onScrollEnd]);

  // Clean up
  useEffect(() => {
    return () => {
      if (scrollThrottleTimerRef.current) {
        clearTimeout(scrollThrottleTimerRef.current);
      }
    };
  }, []);

  return { onScroll };
}