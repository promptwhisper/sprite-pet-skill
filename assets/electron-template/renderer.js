const stage = document.querySelector('#stage');
const petImage = document.querySelector('#pet');
const burst = document.querySelector('#catch-burst');

let animations = {};
let current = 'idle';
let frameIndex = 0;
let accumulator = 0;
let lastTime = performance.now();
let latestState = { pose: 'idle', direction: 1, speed: 0, paused: false };

function applyDisplayScale() {
  const scale = Number(animations[current]?.displayScale || 1);
  petImage.style.setProperty('--display-scale', String(scale));
}

async function loadAnimations() {
  const response = await fetch('assets/animations/manifest.json');
  if (!response.ok) throw new Error(`Animation manifest failed: ${response.status}`);
  const manifest = await response.json();
  animations = Object.fromEntries(manifest.animations.map((animation) => [
    animation.name,
    {
      ...animation,
      frames: animation.frames.map((frame) => `assets/animations/${frame}`),
    },
  ]));
  for (const animation of Object.values(animations)) {
    for (const src of animation.frames) {
      const image = new Image();
      image.src = src;
    }
  }
  current = animations.idle ? 'idle' : Object.keys(animations)[0];
  if (!current) throw new Error('Animation manifest has no animations');
  petImage.src = animations[current].frames[0];
  applyDisplayScale();
  requestAnimationFrame(animate);
}

function selectAnimation(pose) {
  if (animations[pose]) return pose;
  if (pose === 'caught' && animations.caught) return 'caught';
  return animations.idle ? 'idle' : current;
}

function updateState(state) {
  latestState = { ...latestState, ...state };
  const next = selectAnimation(state.pose);
  if (next !== current) {
    current = next;
    frameIndex = 0;
    accumulator = 0;
    petImage.src = animations[current].frames[0];
    applyDisplayScale();
  }
  stage.dataset.pose = state.pose;
  stage.dataset.direction = state.direction < 0 ? 'left' : 'right';
  stage.dataset.paused = String(Boolean(state.paused));
}

function effectiveFps() {
  const base = animations[current].fps || 10;
  if (current === 'walk') return Math.max(7, Math.min(base, 6 + latestState.speed * 1.8));
  if (current === 'run') return Math.max(8, Math.min(20, 8 + latestState.speed * 0.72));
  return base;
}

function animate(now) {
  const animation = animations[current];
  accumulator += Math.min(100, now - lastTime);
  lastTime = now;
  const frameDuration = 1000 / effectiveFps();
  while (accumulator >= frameDuration) {
    accumulator -= frameDuration;
    frameIndex = animation.loop
      ? (frameIndex + 1) % animation.frames.length
      : Math.min(frameIndex + 1, animation.frames.length - 1);
    petImage.src = animation.frames[frameIndex];
  }
  requestAnimationFrame(animate);
}

window.desktopPet.onState(updateState);
window.desktopPet.onCaught(() => {
  burst.classList.remove('visible');
  void burst.offsetWidth;
  burst.classList.add('visible');
});
window.addEventListener('contextmenu', (event) => {
  event.preventDefault();
  window.desktopPet.showMenu();
});
window.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') window.desktopPet.quit();
});

loadAnimations().catch((error) => {
  console.error(error);
  stage.dataset.error = 'true';
});
