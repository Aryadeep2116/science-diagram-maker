// Sample browser animation in a script-disabled, network-isolated iframe.
// A finite set of samples cannot prove that every animation frame is in bounds.
async function sampleAnimatedBounds(svgText) {
  const parsed = new DOMParser().parseFromString(svgText, 'image/svg+xml');
  const source = parsed.documentElement;
  if (!source || source.localName !== 'svg' || parsed.querySelector('parsererror')) {
    return 'Animation sampling could not parse the SVG; review playback manually.';
  }
  const frame = document.createElement('iframe');
  frame.setAttribute('sandbox', 'allow-same-origin'); // no allow-scripts or network permissions
  frame.setAttribute('aria-hidden', 'true');
  frame.tabIndex = -1;
  frame.style.cssText = 'position:fixed;left:-10000px;top:0;width:800px;height:600px;opacity:0;pointer-events:none;border:0';
  frame.srcdoc = '<!doctype html><meta http-equiv="Content-Security-Policy" content="default-src &apos;none&apos;; style-src &apos;unsafe-inline&apos;; img-src &apos;none&apos;; font-src &apos;none&apos;"><body></body>';
  try {
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('renderer timeout')), 4000);
      frame.onload = () => { clearTimeout(timer); resolve(); };
      frame.onerror = () => { clearTimeout(timer); reject(new Error('renderer failed')); };
      document.body.appendChild(frame);
    });
    const doc = frame.contentDocument;
    if (!doc || !doc.body) throw new Error('renderer unavailable');
    const svg = doc.importNode(source, true);
    svg.setAttribute('width', '800');
    svg.setAttribute('height', '600');
    doc.body.appendChild(svg);
    const vb = svg.viewBox.baseVal;
    if (!vb || vb.width <= 0 || vb.height <= 0) throw new Error('invalid viewBox');
    // Let CSS animations initialise, then control their timeline without running SVG scripts.
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    if (svg.pauseAnimations) svg.pauseAnimations();
    const animations = typeof svg.getAnimations === 'function' ? svg.getAnimations({subtree: true}) : [];
    const durations = [];
    for (const node of svg.querySelectorAll('animate,animateTransform,animateMotion,set')) {
      const match = /^\s*(\d+(?:\.\d+)?|\.\d+)\s*(ms|s|min|h)?\s*$/i.exec(node.getAttribute('dur') || '');
      if (match) {
        const factor = {ms: .001, s: 1, min: 60, h: 3600}[String(match[2] || 's').toLowerCase()];
        const seconds = Number(match[1]) * factor;
        if (seconds > 0 && Number.isFinite(seconds)) durations.push(seconds);
      }
    }
    for (const animation of animations) {
      animation.pause();
      const duration = animation.effect && animation.effect.getComputedTiming().duration;
      if (typeof duration === 'number' && duration > 0 && Number.isFinite(duration)) durations.push(duration / 1000);
    }
    const times = new Set([0]);
    for (const duration of durations) {
      for (const fraction of [.25, .5, .75, .99]) times.add(Math.min(duration * fraction, 60));
    }
    const samples = [...times].sort((a, b) => a - b).slice(0, 25);
    const drawables = svg.querySelectorAll('rect,circle,ellipse,line,polyline,polygon,path,text,image,use');
    for (const seconds of samples) {
      if (svg.setCurrentTime) svg.setCurrentTime(seconds);
      for (const animation of animations) animation.currentTime = seconds * 1000;
      for (const node of drawables) {
        if (node.closest('defs,symbol,clipPath,mask,pattern,marker')) continue;
        const style = frame.contentWindow.getComputedStyle(node);
        if (style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity) === 0) continue;
        // Bounding-box approximation is unreliable under clips, masks or filters.
        if ((style.clipPath && style.clipPath !== 'none') || (style.mask && style.mask !== 'none') || (style.filter && style.filter !== 'none')) continue;
        let box, matrix;
        try {
          box = node.getBBox();
          const rootMatrix = svg.getScreenCTM();
          const nodeMatrix = node.getScreenCTM();
          if (!rootMatrix || !nodeMatrix) continue;
          matrix = rootMatrix.inverse().multiply(nodeMatrix);
        } catch (e) { continue; }
        const corners = [[box.x,box.y],[box.x+box.width,box.y],[box.x,box.y+box.height],[box.x+box.width,box.y+box.height]];
        const pts = corners.map(([x,y]) => ({x:matrix.a*x+matrix.c*y+matrix.e, y:matrix.b*x+matrix.d*y+matrix.f}));
        if (pts.some(p => p.x < vb.x - .5 || p.x > vb.x + vb.width + .5 || p.y < vb.y - .5 || p.y > vb.y + vb.height + .5)) {
          return `Possible animated <${node.localName}> overflow near ${seconds.toFixed(2)}s in browser sampling. Inspect playback; bounding boxes can overestimate visible pixels.`;
        }
      }
    }
    return `No overflow detected in ${samples.length} browser animation sample(s). Unsampled times, effects and font differences still require review.`;
  } catch (e) {
    return 'Browser animation sampling was unavailable; review playback manually.';
  } finally {
    frame.remove();
  }
}
