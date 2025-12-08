/**
 * ThinkingBar - ChatGPT-style thinking UI component
 * 
 * Usage:
 *   const thinkingBar = new ThinkingBar('matches'); // context: 'matches' or 'email'
 *   thinkingBar.show();
 *   // ... make API call ...
 *   thinkingBar.hide();
 * 
 * The component automatically cycles through context-appropriate status messages
 * and shows an animated thinking indicator.
 */
(function() {
  'use strict';

  // Message sets for different contexts
  const MESSAGE_SETS = {
    matches: [
      'Thinking...',
      'Analyzing your profile...',
      'Searching labs and PIs...',
      'Evaluating compatibility...',
      'Ranking your matches...'
    ],
    email: [
      'Thinking...',
      'Analyzing the PI profile...',
      'Crafting your email...',
      'Personalizing the message...',
      'Polishing the draft...'
    ],
    default: [
      'Thinking...',
      'Processing your request...',
      'Generating response...'
    ]
  };

  class ThinkingBar {
    constructor(context = 'default') {
      this.context = context;
      this.messages = MESSAGE_SETS[context] || MESSAGE_SETS.default;
      this.currentMessageIndex = 0;
      this.messageInterval = null;
      this.container = null;
      this.isVisible = false;
      
      this.createContainer();
    }

    createContainer() {
      // Create the thinking bar container
      this.container = document.createElement('div');
      this.container.className = 'thinking-bar';
      this.container.setAttribute('aria-live', 'polite');
      this.container.setAttribute('aria-label', 'AI is thinking');
      
      // Create inner structure
      this.container.innerHTML = `
        <div class="thinking-bar-content">
          <div class="thinking-bar-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
          <div class="thinking-bar-message">${this.messages[0]}</div>
        </div>
      `;
      
      // Append to body
      document.body.appendChild(this.container);
      
      // Initially hidden
      this.container.classList.add('thinking-bar-hidden');
    }

    show() {
      if (this.isVisible) return;
      
      this.isVisible = true;
      this.currentMessageIndex = 0;
      this.updateMessage(this.messages[0]);
      
      // Show the bar with animation
      requestAnimationFrame(() => {
        this.container.classList.remove('thinking-bar-hidden');
      });
      
      // Start cycling through messages
      this.startMessageCycle();
    }

    hide() {
      if (!this.isVisible) return;
      
      this.isVisible = false;
      this.stopMessageCycle();
      
      // Hide the bar with animation
      this.container.classList.add('thinking-bar-hidden');
    }

    updateMessage(message) {
      const messageEl = this.container.querySelector('.thinking-bar-message');
      if (messageEl) {
        messageEl.textContent = message;
      }
    }

    startMessageCycle() {
      // Clear any existing interval
      this.stopMessageCycle();
      
      // Change message every 2-3 seconds
      this.messageInterval = setInterval(() => {
        this.currentMessageIndex = (this.currentMessageIndex + 1) % this.messages.length;
        this.updateMessage(this.messages[this.currentMessageIndex]);
      }, 2500);
    }

    stopMessageCycle() {
      if (this.messageInterval) {
        clearInterval(this.messageInterval);
        this.messageInterval = null;
      }
    }

    destroy() {
      this.hide();
      if (this.container && this.container.parentNode) {
        this.container.parentNode.removeChild(this.container);
      }
      this.container = null;
    }

    /**
     * Static helper method to show thinking bar during an async operation
     * 
     * @param {Promise} promise - The async operation to wait for
     * @param {string} context - Context for messages ('matches' or 'email')
     * @returns {Promise} - The original promise
     * 
     * Example:
     *   await ThinkingBar.wrap(fetch('/api/matches'), 'matches');
     */
    static async wrap(promise, context = 'default') {
      const thinkingBar = new ThinkingBar(context);
      thinkingBar.show();
      
      try {
        const result = await promise;
        return result;
      } finally {
        thinkingBar.hide();
        // Clean up after animation completes
        setTimeout(() => thinkingBar.destroy(), 300);
      }
    }
  }

  // Export to global scope
  window.ThinkingBar = ThinkingBar;

})();

