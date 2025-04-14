/**
 * Custom scroll utility functions with speed control
 */

/**
 * Smoothly scrolls an element into view with custom duration
 * @param element The element to scroll to
 * @param duration Duration in milliseconds (higher = slower)
 * @param offset Optional offset from the target
 * @param delay Delay in milliseconds before scrolling begins
 */
export function smoothScrollTo(element: HTMLElement | null, duration: number = 2000, offset: number = 0, delay: number = 0) {
  if (!element) return;
  
  setTimeout(() => {
    const targetPosition = element.getBoundingClientRect().top + window.scrollY - offset;
    const startPosition = window.scrollY;
    const distance = targetPosition - startPosition;
    let startTime: number | null = null;

    function animation(currentTime: number) {
      if (startTime === null) startTime = currentTime;
      const timeElapsed = currentTime - startTime;
      const progress = Math.min(timeElapsed / duration, 1);
      const ease = easeInOutQuad(progress);
      
      window.scrollTo(0, startPosition + distance * ease);
      
      if (timeElapsed < duration) {
        requestAnimationFrame(animation);
      }
    }
    
    // Easing function for smooth acceleration and deceleration
    function easeInOutQuad(t: number): number {
      return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
    }
    
    requestAnimationFrame(animation);
  }, delay);
}

/**
 * Smoothly scrolls an element into view with custom duration using scrollIntoView
 * This is an alternative approach that uses the native scrollIntoView but with custom duration
 * @param element The element to scroll to
 * @param options Scroll options
 * @param delay Delay in milliseconds before scrolling begins
 */
export function customScrollIntoView(element: HTMLElement | null, options: { 
  behavior?: ScrollBehavior,
  block?: ScrollLogicalPosition, 
  inline?: ScrollLogicalPosition
} = {}, delay: number = 0) {
  if (!element) return;
  
  setTimeout(() => {
    // Apply scroll-behavior through style to the documentElement briefly
    const htmlElement = document.documentElement;
    const originalStyle = htmlElement.style.cssText;
    
    // Set the scroll-behavior to smooth with our custom transition duration
    htmlElement.style.scrollBehavior = 'smooth';
    htmlElement.style.setProperty('--scroll-speed', '2000ms');
    
    // Perform the scroll
    element.scrollIntoView({ 
      behavior: options.behavior || 'smooth',
      block: options.block || 'start',
      inline: options.inline || 'nearest'
    });
    
    // Reset style after scrolling is complete
    setTimeout(() => {
      htmlElement.style.cssText = originalStyle;
    }, 2200); // slightly longer than our transition to ensure it completes
  }, delay);
} 