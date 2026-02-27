// Black Hole Animation - Canvas-based realistic black hole with accretion disk
(function() {
  'use strict';

  const canvas = document.getElementById('blackhole-canvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  let width, height, centerX, centerY;
  let animFrame;

  // Configuration
  const CONFIG = {
    blackHoleRadius: 0.08, // fraction of min dimension
    accretionInner: 0.12,
    accretionOuter: 0.35,
    starCount: 200,
    accretionParticles: 300,
    lensingWidth: 0.02,
  };

  // Stars
  let stars = [];
  // Accretion disk particles
  let particles = [];

  function resize() {
    const container = canvas.parentElement;
    width = container.clientWidth;
    height = container.clientHeight;
    canvas.width = width;
    canvas.height = height;
    centerX = width / 2;
    centerY = height / 2;
    initStars();
    initParticles();
  }

  function initStars() {
    stars = [];
    for (let i = 0; i < CONFIG.starCount; i++) {
      stars.push({
        x: Math.random() * width,
        y: Math.random() * height,
        size: Math.random() * 1.5 + 0.5,
        brightness: Math.random(),
        twinkleSpeed: Math.random() * 0.02 + 0.005,
        twinkleOffset: Math.random() * Math.PI * 2,
      });
    }
  }

  function initParticles() {
    particles = [];
    const minDim = Math.min(width, height);
    const innerR = minDim * CONFIG.accretionInner;
    const outerR = minDim * CONFIG.accretionOuter;

    for (let i = 0; i < CONFIG.accretionParticles; i++) {
      const angle = Math.random() * Math.PI * 2;
      const radiusFraction = Math.random();
      const radius = innerR + radiusFraction * (outerR - innerR);
      // Speed inversely proportional to radius (Keplerian)
      const speed = (0.002 + Math.random() * 0.003) * (outerR / radius);
      
      // Color based on radius - inner is hotter (white/orange), outer is cooler (blue/purple)
      let r, g, b;
      if (radiusFraction < 0.3) {
        // Inner - hot white/yellow/orange
        r = 255;
        g = 180 + Math.random() * 75;
        b = 100 + Math.random() * 80;
      } else if (radiusFraction < 0.6) {
        // Mid - orange/red
        r = 220 + Math.random() * 35;
        g = 100 + Math.random() * 80;
        b = 50 + Math.random() * 60;
      } else {
        // Outer - blue/purple
        r = 100 + Math.random() * 60;
        g = 80 + Math.random() * 80;
        b = 180 + Math.random() * 75;
      }

      particles.push({
        angle: angle,
        radius: radius,
        speed: speed,
        size: Math.random() * 2 + 0.5,
        opacity: Math.random() * 0.6 + 0.4,
        r, g, b,
        // Slight vertical offset for 3D tilt effect
        tilt: (Math.random() - 0.5) * 0.3,
        trail: Math.random() * 0.15 + 0.05,
      });
    }
  }

  function drawStars(time) {
    for (const star of stars) {
      const twinkle = Math.sin(time * star.twinkleSpeed + star.twinkleOffset);
      const alpha = 0.3 + (twinkle * 0.5 + 0.5) * 0.7 * star.brightness;
      
      // Don't draw stars behind the black hole area
      const dx = star.x - centerX;
      const dy = star.y - centerY;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const minDim = Math.min(width, height);
      if (dist < minDim * CONFIG.accretionInner) continue;

      ctx.beginPath();
      ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255, 255, 255, ${alpha})`;
      ctx.fill();
    }
  }

  function drawAccretionDisk(time) {
    const minDim = Math.min(width, height);
    
    // Draw particles
    for (const p of particles) {
      p.angle += p.speed;
      
      // Elliptical projection for 3D tilt (disk tilted ~70 degrees)
      const tiltAngle = 0.35; // radians of tilt
      const x = centerX + Math.cos(p.angle) * p.radius;
      const y = centerY + Math.sin(p.angle) * p.radius * Math.sin(tiltAngle) + p.tilt * p.radius * 0.1;
      
      // Particles behind the black hole are dimmer
      const behindFactor = Math.sin(p.angle) > 0 ? 1.0 : 0.3;
      
      // Draw trail
      const trailX = centerX + Math.cos(p.angle - p.trail) * p.radius;
      const trailY = centerY + Math.sin(p.angle - p.trail) * p.radius * Math.sin(tiltAngle) + p.tilt * p.radius * 0.1;
      
      const alpha = p.opacity * behindFactor;
      
      // Trail
      ctx.beginPath();
      ctx.moveTo(trailX, trailY);
      ctx.lineTo(x, y);
      ctx.strokeStyle = `rgba(${p.r}, ${p.g}, ${p.b}, ${alpha * 0.4})`;
      ctx.lineWidth = p.size * 0.8;
      ctx.stroke();
      
      // Particle
      ctx.beginPath();
      ctx.arc(x, y, p.size, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${p.r}, ${p.g}, ${p.b}, ${alpha})`;
      ctx.fill();
    }
  }

  function drawBlackHole() {
    const minDim = Math.min(width, height);
    const bhRadius = minDim * CONFIG.blackHoleRadius;
    
    // Dark center
    const gradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, bhRadius * 1.5);
    gradient.addColorStop(0, 'rgba(0, 0, 0, 1)');
    gradient.addColorStop(0.6, 'rgba(0, 0, 0, 0.98)');
    gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
    
    ctx.beginPath();
    ctx.arc(centerX, centerY, bhRadius * 1.5, 0, Math.PI * 2);
    ctx.fillStyle = gradient;
    ctx.fill();
  }

  function drawLensingRing(time) {
    const minDim = Math.min(width, height);
    const bhRadius = minDim * CONFIG.blackHoleRadius;
    const ringRadius = bhRadius * 1.3;
    const ringWidth = minDim * CONFIG.lensingWidth;
    
    // Pulsing glow
    const pulse = Math.sin(time * 0.001) * 0.15 + 0.85;
    
    // Outer glow
    const glowGrad = ctx.createRadialGradient(centerX, centerY, ringRadius - ringWidth * 2, centerX, centerY, ringRadius + ringWidth * 3);
    glowGrad.addColorStop(0, 'rgba(139, 124, 248, 0)');
    glowGrad.addColorStop(0.3, `rgba(139, 124, 248, ${0.15 * pulse})`);
    glowGrad.addColorStop(0.5, `rgba(200, 180, 255, ${0.3 * pulse})`);
    glowGrad.addColorStop(0.7, `rgba(139, 124, 248, ${0.15 * pulse})`);
    glowGrad.addColorStop(1, 'rgba(139, 124, 248, 0)');
    
    ctx.beginPath();
    ctx.arc(centerX, centerY, ringRadius + ringWidth * 3, 0, Math.PI * 2);
    ctx.fillStyle = glowGrad;
    ctx.fill();
    
    // Bright ring
    ctx.beginPath();
    ctx.arc(centerX, centerY, ringRadius, 0, Math.PI * 2);
    ctx.strokeStyle = `rgba(200, 190, 255, ${0.6 * pulse})`;
    ctx.lineWidth = ringWidth;
    ctx.stroke();
    
    // Inner bright edge
    ctx.beginPath();
    ctx.arc(centerX, centerY, ringRadius - ringWidth * 0.3, 0, Math.PI * 2);
    ctx.strokeStyle = `rgba(255, 255, 255, ${0.3 * pulse})`;
    ctx.lineWidth = ringWidth * 0.3;
    ctx.stroke();
  }

  function drawNebulaGlow(time) {
    const minDim = Math.min(width, height);
    const outerR = minDim * CONFIG.accretionOuter;
    
    // Soft nebula glow behind the accretion disk
    const nebulaGrad = ctx.createRadialGradient(centerX, centerY, minDim * CONFIG.accretionInner, centerX, centerY, outerR * 1.2);
    nebulaGrad.addColorStop(0, 'rgba(139, 92, 246, 0.05)');
    nebulaGrad.addColorStop(0.4, 'rgba(99, 102, 241, 0.03)');
    nebulaGrad.addColorStop(0.7, 'rgba(59, 130, 246, 0.02)');
    nebulaGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
    
    ctx.beginPath();
    ctx.arc(centerX, centerY, outerR * 1.2, 0, Math.PI * 2);
    ctx.fillStyle = nebulaGrad;
    ctx.fill();
  }

  function draw(time) {
    ctx.clearRect(0, 0, width, height);
    
    // Layer order: stars -> nebula -> accretion (behind) -> lensing ring -> black hole -> accretion (front)
    drawStars(time);
    drawNebulaGlow(time);
    drawAccretionDisk(time);
    drawLensingRing(time);
    drawBlackHole();
    
    animFrame = requestAnimationFrame(draw);
  }

  // Initialize
  resize();
  window.addEventListener('resize', resize);
  animFrame = requestAnimationFrame(draw);
})();
