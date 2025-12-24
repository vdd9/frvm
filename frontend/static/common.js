/**
 * FRVM - Common utilities shared between index.html and player.html
 */

/**
 * Show a tooltip overlay for category emojis (for mobile long-press)
 * @param {string} emoji - The emoji to display
 * @param {string} text - The tooltip text
 */
function showCategoryTooltip(emoji, text) {
  let overlay = document.getElementById('categoryTooltip');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'categoryTooltip';
    overlay.className = 'category-tooltip-overlay';
    document.body.appendChild(overlay);
  }
  overlay.innerHTML = `<span class="emoji">${emoji}</span>${text}`;
  overlay.classList.add('visible');
  setTimeout(() => overlay.classList.remove('visible'), 1500);
}

/**
 * Setup long-press tooltip for an element (mobile support)
 * @param {HTMLElement} element - The element to attach long-press to
 * @param {string} emoji - The emoji to show in tooltip
 * @param {string} tooltipText - The text to show in tooltip
 */
function setupLongPressTooltip(element, emoji, tooltipText) {
  let longPressTimer = null;
  
  element.addEventListener('touchstart', (e) => {
    longPressTimer = setTimeout(() => {
      showCategoryTooltip(emoji, tooltipText);
    }, 400);
  }, { passive: true });
  
  element.addEventListener('touchend', () => {
    clearTimeout(longPressTimer);
  });
  
  element.addEventListener('touchmove', () => {
    clearTimeout(longPressTimer);
  });
}

/**
 * Adjust a panel's size to fit content in max 2 lines
 * @param {HTMLElement} panel - The panel container
 * @param {string} itemSelector - CSS selector for items to measure
 * @param {string[]} levels - Array of class names for progressive compaction
 */
function adjustPanelSize(panel, itemSelector, levels = ['compact', 'very-compact', 'ultra-compact']) {
  if (!panel) return;
  
  // Reset classes first
  levels.forEach(l => panel.classList.remove(l));
  
  const items = panel.querySelectorAll(itemSelector);
  if (items.length === 0) return;
  
  // Count lines by checking how many unique Y positions we have
  const getLineCount = () => {
    const yPositions = new Set();
    items.forEach(item => {
      yPositions.add(Math.round(item.getBoundingClientRect().top));
    });
    return yPositions.size;
  };
  
  let lines = getLineCount();
  
  // Progressively add compact classes until we fit in 2 lines
  for (const level of levels) {
    if (lines <= 2) break;
    
    // Remove previous levels and add current
    levels.forEach(l => panel.classList.remove(l));
    panel.classList.add(level);
    
    // Force reflow
    void panel.offsetHeight;
    
    lines = getLineCount();
  }
}
