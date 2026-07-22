const path = require('node:path');
const { app, BrowserWindow, Menu, globalShortcut, ipcMain, screen } = require('electron');

const CONFIG = {
  width: 270,
  height: 220,
  chaseRadius: 520,
  pounceRadius: 165,
  catchRadius: 52,
  followStopRadius: 108,
  pounceRearmRadius: 260,
  pounceCooldown: 4200,
  pounceDuration: 690,
};

let petWindow;
let timer;
let paused = false;
let pounceUntil = 0;
let caughtUntil = 0;
let nextPounceAt = 0;
let pounceArmed = true;
let nextWanderAt = 0;
let wanderTargetX = 0;
let ignoringMouse;
const pet = { x: 0, y: 0, vx: 0, vy: 0, direction: 1 };
const hasSingleInstanceLock = app.requestSingleInstanceLock();

function workArea() {
  return petWindow ? screen.getDisplayMatching(petWindow.getBounds()).workArea : screen.getPrimaryDisplay().workArea;
}

function home(area = workArea()) {
  return {
    x: area.x + Math.round((area.width - CONFIG.width) / 2),
    y: area.y + area.height - CONFIG.height,
  };
}

function setHome() {
  const position = home();
  Object.assign(pet, position, { vx: 0, vy: 0 });
  wanderTargetX = pet.x + CONFIG.width / 2;
  nextWanderAt = Date.now() + 1200;
  petWindow?.setPosition(Math.round(pet.x), Math.round(pet.y), false);
}

function approach(value, target, maxDelta) {
  if (value < target) return Math.min(value + maxDelta, target);
  if (value > target) return Math.max(value - maxDelta, target);
  return value;
}

function arrive(targetX, targetY, options) {
  const dx = targetX - (pet.x + CONFIG.width / 2);
  const dy = targetY - (pet.y + CONFIG.height / 2);
  const distance = Math.hypot(dx, dy);
  const settleTolerance = 5;
  if (options.retreat && distance > 0 && distance < options.stopRadius - settleTolerance) {
    const desiredSpeed = 2.8 * Math.min(1, (options.stopRadius - distance) / 80);
    pet.vx = approach(pet.vx, -(dx / distance) * desiredSpeed, 0.35);
    pet.vy = approach(pet.vy, -(dy / distance) * desiredSpeed, 0.35);
    return { distance, settled: false };
  }
  if (distance <= options.stopRadius + settleTolerance) {
    pet.vx = Math.abs(pet.vx * options.brake) < 0.03 ? 0 : pet.vx * options.brake;
    pet.vy = Math.abs(pet.vy * options.brake) < 0.03 ? 0 : pet.vy * options.brake;
    return { distance, settled: true };
  }
  const remaining = Math.max(0, distance - options.stopRadius);
  const desiredSpeed = options.maxSpeed * Math.min(1, remaining / options.slowRadius);
  pet.vx = approach(pet.vx, (dx / distance) * desiredSpeed, options.acceleration);
  pet.vy = approach(pet.vy, (dy / distance) * desiredSpeed, options.acceleration);
  return { distance, settled: false };
}

function damp(amount = 0.82) {
  pet.vx *= amount;
  pet.vy *= amount;
  if (Math.abs(pet.vx) < 0.03) pet.vx = 0;
  if (Math.abs(pet.vy) < 0.03) pet.vy = 0;
}

function clamp(area) {
  pet.x = Math.max(area.x, Math.min(pet.x, area.x + area.width - CONFIG.width));
  pet.y = Math.max(area.y, Math.min(pet.y, area.y + area.height - CONFIG.height));
}

function setMousePassThrough(ignore) {
  if (!petWindow || ignore === ignoringMouse) return;
  ignoringMouse = ignore;
  petWindow.setIgnoreMouseEvents(ignore, { forward: true });
}

function update() {
  if (!petWindow || petWindow.isDestroyed()) return;
  const now = Date.now();
  const cursor = screen.getCursorScreenPoint();
  const area = workArea();
  const centerX = pet.x + CONFIG.width / 2;
  const centerY = pet.y + CONFIG.height / 2;
  const distance = Math.hypot(cursor.x - centerX, cursor.y - centerY);
  let pose = 'idle';

  if (!pounceArmed && distance > CONFIG.pounceRearmRadius) pounceArmed = true;
  setMousePassThrough(distance > CONFIG.followStopRadius);
  if (paused) {
    damp(0.76);
  } else if (now < caughtUntil) {
    damp(0.68);
    pose = 'caught';
  } else if (now < pounceUntil) {
    arrive(cursor.x, cursor.y, {
      maxSpeed: 15, acceleration: 1.4, slowRadius: 130, stopRadius: 24, brake: 0.62,
    });
    pose = 'pounce';
    if (distance < CONFIG.catchRadius) {
      caughtUntil = now + 850;
      pounceUntil = now;
      nextPounceAt = caughtUntil + CONFIG.pounceCooldown;
      pounceArmed = false;
      petWindow.webContents.send('cursor-caught');
    }
  } else if (pounceArmed && distance < CONFIG.pounceRadius && now >= nextPounceAt) {
    pounceArmed = false;
    pounceUntil = now + CONFIG.pounceDuration;
    nextPounceAt = pounceUntil + CONFIG.pounceCooldown;
    pose = 'pounce';
  } else if (distance < CONFIG.chaseRadius) {
    const arrival = arrive(cursor.x, cursor.y, {
      maxSpeed: 8.5,
      acceleration: 0.75,
      slowRadius: 240,
      stopRadius: CONFIG.followStopRadius,
      brake: 0.68,
      retreat: true,
    });
    const speed = Math.hypot(pet.vx, pet.vy);
    pose = arrival.settled ? 'idle' : speed < 3.2 ? 'walk' : 'run';
  } else {
    const bottomY = area.y + area.height - CONFIG.height / 2;
    if (now >= nextWanderAt) {
      wanderTargetX = area.x + CONFIG.width / 2 + Math.random() * Math.max(1, area.width - CONFIG.width);
      nextWanderAt = now + 2600 + Math.random() * 3200;
    }
    if (Math.abs(wanderTargetX - centerX) > 28) {
      const arrival = arrive(wanderTargetX, bottomY, {
        maxSpeed: 2.3, acceleration: 0.18, slowRadius: 160, stopRadius: 24, brake: 0.68,
      });
      pose = arrival.settled ? 'idle' : 'walk';
    } else {
      damp();
    }
  }

  pet.x += pet.vx;
  pet.y += pet.vy;
  clamp(area);
  if (Math.abs(pet.vx) > 0.25) pet.direction = pet.vx >= 0 ? 1 : -1;
  petWindow.setPosition(Math.round(pet.x), Math.round(pet.y), false);
  petWindow.webContents.send('pet-state', {
    pose,
    direction: pet.direction,
    speed: Math.hypot(pet.vx, pet.vy),
    paused,
  });
}

function showMenu() {
  const menu = Menu.buildFromTemplate([
    {
      label: paused ? 'Resume pet' : 'Pause pet',
      click: () => { paused = !paused; },
    },
    { label: 'Return to bottom', click: setHome },
    { type: 'separator' },
    { label: 'Quit desktop pet', click: () => app.quit() },
  ]);
  menu.popup({ window: petWindow });
}

function createWindow() {
  const position = home(screen.getPrimaryDisplay().workArea);
  petWindow = new BrowserWindow({
    width: CONFIG.width,
    height: CONFIG.height,
    ...position,
    frame: false,
    transparent: true,
    backgroundColor: '#00000000',
    resizable: false,
    maximizable: false,
    minimizable: false,
    fullscreenable: false,
    hasShadow: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  petWindow.setAlwaysOnTop(true, 'floating');
  petWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  petWindow.loadFile('index.html');
  petWindow.once('ready-to-show', () => {
    setHome();
    petWindow.showInactive();
    timer = setInterval(update, 16);
  });
  petWindow.on('closed', () => {
    clearInterval(timer);
    petWindow = undefined;
  });
}

if (!hasSingleInstanceLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (!petWindow || petWindow.isDestroyed()) return;
    petWindow.setAlwaysOnTop(true, 'floating');
    petWindow.showInactive();
  });
  ipcMain.on('show-pet-menu', showMenu);
  ipcMain.on('quit-pet', () => app.quit());
  app.whenReady().then(() => {
    createWindow();
    globalShortcut.register('CommandOrControl+Alt+Q', () => app.quit());
  });
  app.on('window-all-closed', () => app.quit());
  app.on('will-quit', () => globalShortcut.unregisterAll());
}
