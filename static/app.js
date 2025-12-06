// RIQ Lab Matcher - Main JavaScript File

(function() {
  'use strict';

  // ===== Page Transitions =====
  function initPageTransitions() {
    const main = document.querySelector('main.page');
    if (!main) return;

    // Add enter animation on page load
    main.classList.add('page-enter');
    
    main.addEventListener('animationend', function() {
      main.classList.remove('page-enter');
    }, { once: true });

    // Handle internal link clicks
    document.addEventListener('click', function(e) {
      const link = e.target.closest('a');
      if (!link) return;

      const href = link.getAttribute('href');
      if (!href) return;

      // Skip if:
      // - External link
      // - Opens in new tab
      // - Download link
      // - Hash link (same page anchor)
      // - Form button (special handling)
      if (link.target === '_blank' ||
          link.download ||
          href.startsWith('http') ||
          href.startsWith('mailto:') ||
          href.startsWith('#') ||
          link.closest('form')) {
        return;
      }

      // Skip if clicking on a form submit button inside a link
      if (link.querySelector('button[type="submit"]')) {
        return;
      }

      // Only handle same-origin navigation
      try {
        const url = new URL(href, window.location.origin);
        if (url.origin !== window.location.origin) return;
      } catch (err) {
        // Relative URL, proceed
      }

      e.preventDefault();
      
      // Add exit animation
      main.classList.add('page-exit');
      
      // Navigate after animation
      setTimeout(() => {
        window.location.href = href;
      }, 200);
    });
  }

  // ===== Card Animations (IntersectionObserver) =====
  function initCardAnimations() {
    const cards = document.querySelectorAll('.pi-list .pi-card, .help-section, .match-row');
    if (cards.length === 0) return;

    // Add initial hidden state
    cards.forEach((card, index) => {
      card.classList.add('card-hidden');
    });

    // Create IntersectionObserver
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.remove('card-hidden');
          entry.target.classList.add('card-visible');
          observer.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.1,
      rootMargin: '0px 0px -50px 0px'
    });

    // Observe each card with staggered delay
    cards.forEach((card, index) => {
      // Apply inline delay based on index
      card.style.animationDelay = `${index * 80}ms`;
      observer.observe(card);
    });
  }

  // ===== Match Score Animation =====
  function animateScoreCircle(circle) {
    const score = parseInt(circle.getAttribute('data-score')) || 0;
    const progress = (score / 100) * 360;
    
    // Set CSS custom property for conic gradient
    circle.style.setProperty('--progress', `${progress}deg`);
    
    // Animate number count-up
    const numberEl = circle.querySelector('.score-number');
    if (!numberEl) return;
    
    const duration = 1000; // 1 second
    const start = 0;
    const end = score;
    const startTime = performance.now();
    
    function updateNumber(currentTime) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      
      // Easing function (ease-out)
      const easeProgress = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(start + (end - start) * easeProgress);
      
      numberEl.textContent = current;
      
      if (progress < 1) {
        requestAnimationFrame(updateNumber);
      } else {
        numberEl.textContent = end;
      }
    }
    
    // Start animation when card becomes visible
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          requestAnimationFrame(updateNumber);
          observer.unobserve(circle);
        }
      });
    }, { threshold: 0.5 });
    
    observer.observe(circle);
  }

  function initScoreAnimations() {
    const scoreCircles = document.querySelectorAll('.score-circle[data-score]');
    scoreCircles.forEach(circle => {
      animateScoreCircle(circle);
    });
  }

  // ===== Nav Scroll Effect =====
  function initNavScroll() {
    const nav = document.querySelector('.top-nav');
    if (!nav) return;

    let lastScroll = 0;
    const scrollThreshold = 10;

    function handleScroll() {
      const currentScroll = window.scrollY;
      
      if (currentScroll > scrollThreshold) {
        nav.classList.add('nav-scrolled');
      } else {
        nav.classList.remove('nav-scrolled');
      }
      
      lastScroll = currentScroll;
    }

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll(); // Initial check
  }

  // ===== Card Click Micro-interaction =====
  function initCardPress() {
    const cards = document.querySelectorAll('.pi-card');
    
    cards.forEach(card => {
      let isPressed = false;
      
      card.addEventListener('mousedown', function() {
        if (!isPressed) {
          isPressed = true;
          card.classList.add('card-pressed');
        }
      });
      
      card.addEventListener('mouseup', function() {
        if (isPressed) {
          setTimeout(() => {
            card.classList.remove('card-pressed');
            isPressed = false;
          }, 150);
        }
      });
      
      card.addEventListener('mouseleave', function() {
        if (isPressed) {
          card.classList.remove('card-pressed');
          isPressed = false;
        }
      });
      
      // Handle touch for mobile
      card.addEventListener('touchstart', function() {
        if (!isPressed) {
          isPressed = true;
          card.classList.add('card-pressed');
        }
      });
      
      card.addEventListener('touchend', function() {
        if (isPressed) {
          setTimeout(() => {
            card.classList.remove('card-pressed');
            isPressed = false;
          }, 150);
        }
      });
    });
  }

  // ===== Science Constellation Parallax =====
  function initConstellationParallax() {
    const constellation = document.querySelector('.science-constellation');
    if (!constellation) return;

    const elements = constellation.querySelectorAll('.constellation-element');
    if (elements.length === 0) return;

    let mouseX = 0;
    let mouseY = 0;
    let targetX = 0;
    let targetY = 0;

    function handleMouseMove(e) {
      const rect = constellation.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      
      mouseX = (e.clientX - centerX) / rect.width;
      mouseY = (e.clientY - centerY) / rect.height;
    }

    function animate() {
      // Smooth interpolation
      targetX += (mouseX - targetX) * 0.1;
      targetY += (mouseY - targetY) * 0.1;

      elements.forEach((el, index) => {
        const intensity = 20 + (index * 5); // Different intensity per element
        const x = targetX * intensity;
        const y = targetY * intensity;
        el.style.transform = `translate(${x}px, ${y}px)`;
      });

      requestAnimationFrame(animate);
    }

    constellation.addEventListener('mousemove', handleMouseMove);
    constellation.addEventListener('mouseleave', function() {
      mouseX = 0;
      mouseY = 0;
    });

    animate();
  }

  // ===== Lab Detail Panel (Optional Quick View) =====
  function initLabDetailPanel() {
    const cards = document.querySelectorAll('.pi-card');
    const panel = document.querySelector('.lab-detail-panel');
    if (!panel || cards.length === 0) return;

    const closeBtn = panel.querySelector('.close-panel');
    if (closeBtn) {
      closeBtn.addEventListener('click', function() {
        panel.classList.remove('open');
      });
    }

    cards.forEach(card => {
      card.addEventListener('click', function(e) {
        // Don't trigger if clicking a button or link
        if (e.target.closest('button, a, form')) return;
        
        // Get PI info from card
        const nameEl = card.querySelector('h2');
        const titleEl = card.querySelector('.pi-title');
        const locationEl = card.querySelector('.pi-location');
        const researchEl = card.querySelector('.pi-research');
        
        if (nameEl) {
          // Update panel content (simplified - just show name and basic info)
          const panelTitle = panel.querySelector('.panel-header h2');
          if (panelTitle) panelTitle.textContent = nameEl.textContent;
          
          // You could populate more details here if needed
          panel.classList.add('open');
        }
      });
    });

    // Close panel on escape key
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && panel.classList.contains('open')) {
        panel.classList.remove('open');
      }
    });
  }

  // ===== Technique Multi-select =====
  function initTechniqueMultiSelect() {
    const techniqueInput = document.getElementById('technique-input');
    const techniquePills = document.querySelectorAll('.technique-pill');
    
    if (!techniqueInput || techniquePills.length === 0) return;

    // Track selected techniques
    let selected = [];
    
    // Parse initial value if present (comma-separated or single value)
    const initialValue = techniqueInput.value.trim();
    if (initialValue) {
      // Handle both comma-separated and single values
      const initialSelected = initialValue.split(',').map(s => s.trim()).filter(s => s);
      initialSelected.forEach(value => {
        if (!selected.includes(value)) {
          selected.push(value);
        }
        // Mark corresponding pill as selected
        techniquePills.forEach(pill => {
          if (pill.getAttribute('data-value') === value || pill.textContent.trim() === value) {
            pill.classList.add('selected');
          }
        });
      });
      // Update input with parsed values (ensures consistent format)
      if (selected.length > 0) {
        techniqueInput.value = selected.join(',');
      }
    }

    // Handle pill clicks
    techniquePills.forEach(pill => {
      pill.addEventListener('click', function() {
        const value = this.getAttribute('data-value');
        const index = selected.indexOf(value);
        
        if (index > -1) {
          // Deselect
          selected.splice(index, 1);
          this.classList.remove('selected');
        } else {
          // Select
          selected.push(value);
          this.classList.add('selected');
        }
        
        // Update hidden input
        techniqueInput.value = selected.join(',');
      });
    });
  }

  // ===== Initialize Everything =====
  function init() {
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', init);
      return;
    }

    initPageTransitions();
    initCardAnimations();
    initScoreAnimations();
    initNavScroll();
    initCardPress();
    initConstellationParallax();
    initLabDetailPanel();
    initTechniqueMultiSelect();
  }

  // Start initialization
  init();

})();

