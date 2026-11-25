// Moin Hamburg showcase: the real renderer (custom_components/moin_hamburg/render)
// running in the browser with Pyodide. tools/showcase.py builds the files next to this one.

const MOON = ['new moon', 'waxing crescent', 'first quarter', 'waxing gibbous', 'full moon',
  'waning gibbous', 'last quarter', 'waning crescent'];
const TIDE = ['low tide', 'a quarter up', 'half tide', 'three quarters up', 'high tide'];
const LABELS = {
  time: { day: 'Day', dusk: 'Dusk', night: 'Night' },
  weather: { clear: 'Clear', cloudy: 'Cloudy', rain: 'Rain', snow: 'Snow' },
  season: { spring: 'Spring', summer: 'Summer', autumn: 'Autumn', winter: 'Winter' },
  wind: { calm: 'Calm', windy: 'Windy', storm: 'Storm' },
  direction: { west: 'West', east: 'East' },
  extremes: { heat: 'Heat', cold: 'Cold', 'snow-cover': 'Snow cover', fog: 'Fog', thunder: 'Thunder',
    'storm-surge': 'Storm surge', 'ice-drift': 'Ice drift' },
  ships: { cruise: 'Cruise ship at the terminal', container: 'Container ship under way' },
  warnings: { hurricane: 'Hurricane', 'storm-surge': 'Storm surge', 'storm-gusts': 'Storm gusts', thunder: 'Thunderstorm',
    heat: 'Heat', frost: 'Severe frost', snow: 'Snow' },
};
const TEMPERATURE = { spring: 13, summer: 23, autumn: 9, winter: 1 };

const $ = (id) => document.getElementById(id);
let data, render = null, parseKey = null, url = null, pending = 0, HELP = '';
const s = { time: 'dusk', weather: 'clear', season: 'summer', wind: 'calm', direction: 'west', moon: 4, tide: 'none',
  warning: 'none', day: 'none', extremes: new Set(), ships: new Set(), animated: true, cards: true };

function key() {
  const p = [`${s.time}-${s.weather}`, s.season, `wind-${s.wind}` + (s.wind === 'calm' ? '' : `-${s.direction}`)];
  if (s.time === 'night' && s.weather === 'clear') p.push(`moon-${s.moon}`);
  if (s.tide !== 'none') p.push(`tide-${s.tide}`);
  p.push(...[...s.extremes].sort());
  p.push(...[...s.ships].sort().map((k) => `ship-${k}`));
  if (s.warning !== 'none') p.push(`warning-${s.warning}`);
  if (s.day !== 'none') p.push(`event-${s.day}`);
  return p.join('.');
}

function fromKey(k) {
  const st = parseKey(k).toJs({ dict_converter: Object.fromEntries });
  const [time, weather] = st.scene.split('-');
  Object.assign(s, { time, weather, season: st.season, wind: st.wind, direction: st.direction < 0 ? 'east' : 'west',
    warning: st.warning, day: st.day, extremes: new Set(st.extremes), ships: new Set(st.ships) });
  if (st.moon !== null && st.moon !== undefined) s.moon = st.moon;
  s.tide = st.tide === null || st.tide === undefined ? 'none' : String(st.tide);
}

// --- the picture ---------------------------------------------------------

function show(src) {
  if (url) URL.revokeObjectURL(url);
  url = src.startsWith('<') ? URL.createObjectURL(new Blob([src], { type: 'image/svg+xml' })) : null;
  $('stage').style.backgroundImage = `url("${url || src}")`;
}

function colors() {
  const c = data.colors[`${s.time}-${s.weather}`];
  for (const [k, v] of Object.entries(c)) document.documentElement.style.setProperty(`--${k}`, v);
}

function mock() {
  const t = data.texts;
  const temp = s.extremes.has('heat') ? 31 : s.extremes.has('cold') ? -9 : TEMPERATURE[s.season];
  const night = s.time !== 'day';
  $('mock-greeting').textContent = t[{ day: 'day', dusk: 'evening', night: 'night' }[s.time]];
  $('mock-wish').textContent = s.day === 'birthday' ? t.birthday.replace('{name}', 'Kim') : (t[s.day] || '');
  let summary;
  if (s.weather === 'rain' || s.weather === 'snow') {
    summary = t.until.replace('{t}', temp).replace('{wet}', t[s.weather]).replace('{h}', night ? 23 : 15);
  } else {
    const sky = s.weather === 'cloudy' ? t.cloudy : night ? t['clear-night'] : t['clear-day'];
    summary = (night ? t.later : t['up-to']).replace('{t}', temp).replace('{sky}', sky)
      .replace('{low}', temp - 3).replace('{high}', temp + 3);
  }
  $('mock-summary').textContent = summary;
  $('mock').hidden = !s.cards;
}

function draw(fallback) {
  const k = key();
  $('key').value = k;
  $('key').removeAttribute('aria-invalid');
  if ($('key-help').classList.contains('error')) {
    $('key-help').innerHTML = HELP;
    $('key-help').classList.remove('error');
  }
  colors();
  mock();
  sync();
  if (render) {
    cancelAnimationFrame(pending);
    pending = requestAnimationFrame(() => show(render(k, s.animated)));
  } else if (fallback) {
    show(fallback);
  }
}

// --- controls ------------------------------------------------------------

function segment(name, options, labels) {
  const box = document.querySelector(`.seg[data-name="${name}"]`);
  for (const o of options) {
    const b = document.createElement('button');
    b.type = 'button';
    b.dataset.value = o;
    b.textContent = labels[o] || o;
    b.addEventListener('click', () => { s[name] = o; draw(); });
    box.append(b);
  }
}

function options(select, list) {
  for (const [value, label] of list) select.add(new Option(label, value));
}

function sync() {
  for (const box of document.querySelectorAll('.seg')) {
    for (const b of box.querySelectorAll('button')) b.setAttribute('aria-pressed', String(s[box.dataset.name] === b.dataset.value));
  }
  for (const b of document.querySelectorAll('.seg[data-name="direction"] button')) b.disabled = s.wind === 'calm';
  $('moon').value = String(s.moon);
  $('moon').disabled = !(s.time === 'night' && s.weather === 'clear');
  $('tide').value = s.tide;
  $('warning').value = s.warning;
  $('day').value = s.day;
  for (const c of document.querySelectorAll('#extremes input')) c.checked = s.extremes.has(c.value);
  for (const c of document.querySelectorAll('#ships input')) c.checked = s.ships.has(c.value);
  $('animated').checked = s.animated;
  $('cards').checked = s.cards;
}

function controls() {
  segment('time', data.times, LABELS.time);
  segment('weather', data.weathers, LABELS.weather);
  segment('season', data.seasons, LABELS.season);
  segment('wind', data.winds, LABELS.wind);
  segment('direction', ['west', 'east'], LABELS.direction);
  options($('moon'), MOON.map((m, i) => [String(i), m]));
  options($('tide'), [['none', 'No gauge'], ...TIDE.map((t, i) => [String(i), t])]);
  options($('warning'), [['none', 'None'], ...data.warnings.map((w) => [w, LABELS.warnings[w] || w])]);
  options($('day'), [['none', 'None'], ...data.days.map((d) => [d.id, d.name])]);
  for (const e of data.extremes) {
    const l = document.createElement('label');
    l.innerHTML = `<input type="checkbox" value="${e}"> ${LABELS.extremes[e] || e}`;
    l.querySelector('input').addEventListener('change', (ev) => {
      ev.target.checked ? s.extremes.add(e) : s.extremes.delete(e);
      draw();
    });
    $('extremes').append(l);
  }
  for (const k of data.ships) {
    const l = document.createElement('label');
    l.innerHTML = `<input type="checkbox" value="${k}"> ${LABELS.ships[k] || k}`;
    l.querySelector('input').addEventListener('change', (ev) => {
      ev.target.checked ? s.ships.add(k) : s.ships.delete(k);
      draw();
    });
    $('ships').append(l);
  }
  $('moon').addEventListener('change', (e) => { s.moon = Number(e.target.value); draw(); });
  $('tide').addEventListener('change', (e) => { s.tide = e.target.value; draw(); });
  $('warning').addEventListener('change', (e) => { s.warning = e.target.value; draw(); });
  $('day').addEventListener('change', (e) => { s.day = e.target.value; draw(); });
  $('animated').addEventListener('change', (e) => { s.animated = e.target.checked; draw(); });
  $('cards').addEventListener('change', (e) => { s.cards = e.target.checked; mock(); });
  $('keyform').addEventListener('submit', (e) => {
    e.preventDefault();
    if (!parseKey) return;
    try {
      fromKey($('key').value.trim());
      draw();
    } catch (err) {
      $('key').setAttribute('aria-invalid', 'true');
      $('key-help').textContent = String(err.message).trim().split('\n').pop().replace(/^[\w.]*InvalidKey: /, 'Not a state key: ');
      $('key-help').classList.add('error');
    }
  });
  $('copy').addEventListener('click', () => navigator.clipboard?.writeText($('key').value));
}

function days() {
  const list = $('days');
  for (const d of data.days) {
    const li = document.createElement('li');
    li.className = 'day';
    li.innerHTML = `<button type="button" aria-label="Show ${d.name}"><img src="days/${d.id}.svg" alt="" loading="lazy"></button>
      <div class="day-body"><h3>${d.name} <span class="de" lang="de">${d.name_de}</span></h3><p>${d.when}</p></div>`;
    if (d.keywords.length) {
      const chips = document.createElement('div');
      chips.className = 'chips';
      for (const k of d.keywords) {
        const c = document.createElement('code');
        c.textContent = k;
        chips.append(c);
      }
      li.querySelector('.day-body').append(chips);
    }
    li.querySelector('button').addEventListener('click', () => {
      if (parseKey) fromKey(d.key);
      else Object.assign(s, guess(d.key));
      draw(`days/${d.id}.svg`);
      $('stage').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
    });
    list.append(li);
  }
}

// Before the generator is loaded: read a key well enough to set the controls.
function guess(k) {
  const p = k.split('.');
  const [time, weather] = p[0].split('-');
  const w = p[2].split('-');
  const out = { time, weather, season: p[1], wind: w[1], direction: w[2] || 'west', tide: 'none', warning: 'none',
    day: 'none', extremes: new Set(), ships: new Set() };
  for (const x of p.slice(3)) {
    if (x.startsWith('moon-')) out.moon = Number(x.slice(5));
    else if (x.startsWith('tide-')) out.tide = x.slice(5);
    else if (x.startsWith('ship-')) out.ships.add(x.slice(5));
    else if (x.startsWith('warning-')) out.warning = x.slice(8);
    else if (x.startsWith('event-')) out.day = x.slice(6);
    else out.extremes.add(x);
  }
  return out;
}

// --- the demo calendar ---------------------------------------------------

function ics() {
  const events = data.days.filter((d) => d.title);
  const pad = (n) => String(n).padStart(2, '0');
  const ymd = (d) => `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}`;
  const esc = (t) => t.replace(/[\\;,]/g, (c) => `\\${c}`);
  const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d+/, '');
  const lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Moin Hamburg//Demo calendar//EN', 'CALSCALE:GREGORIAN',
    'X-WR-CALNAME:Moin Hamburg demo'];
  const day = new Date();
  events.forEach((d, i) => {
    const start = new Date(day.getFullYear(), day.getMonth(), day.getDate() + 1 + i);
    const end = new Date(start.getFullYear(), start.getMonth(), start.getDate() + 1);
    lines.push('BEGIN:VEVENT', `UID:moin-hamburg-demo-${d.id}-${ymd(start)}`, `DTSTAMP:${stamp}`,
      `DTSTART;VALUE=DATE:${ymd(start)}`, `DTEND;VALUE=DATE:${ymd(end)}`, `SUMMARY:${esc(d.title)}`,
      `DESCRIPTION:${esc(`Moin Hamburg demo: shows ${d.name}. Not the real date.`)}`, 'TRANSP:TRANSPARENT', 'END:VEVENT');
  });
  lines.push('END:VCALENDAR');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([lines.join('\r\n') + '\r\n'], { type: 'text/calendar' }));
  a.download = 'moin-hamburg-demo.ics';
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

// --- start ---------------------------------------------------------------

async function generator() {
  const status = $('status');
  try {
    const { loadPyodide } = await import(`${data.pyodide}pyodide.mjs`);
    const py = await loadPyodide({ indexURL: data.pyodide });
    py.FS.mkdirTree('/showcase/render');
    await Promise.all(data.files.map(async (f) => {
      const r = await fetch(`py/render/${f}?v=${data.build}`);
      if (!r.ok) throw new Error(`py/render/${f}: ${r.status}`);
      py.FS.writeFile(`/showcase/render/${f}`, await r.text());
    }));
    py.runPython("import sys; sys.path.insert(0, '/showcase')");
    const mod = py.pyimport('render');
    render = (k, animated) => mod.render(k, animated);
    parseKey = (k) => mod.parse_key(k);
    status.textContent = 'Generator ready — Python in your browser';
    status.classList.add('ready');
    draw();
  } catch (err) {
    console.error(err);
    status.textContent = 'The generator could not load — the pictures below still work';
    status.classList.add('error');
  }
}

async function main() {
  data = await (await fetch('data.json', { cache: 'no-cache' })).json();
  HELP = $('key-help').innerHTML;
  Object.assign(s, guess(data.hero));
  controls();
  days();
  $('ics').addEventListener('click', ics);
  $('version').textContent = data.version;
  $('repo-link').href = `https://github.com/${data.repo}`;
  $('repo-name').textContent = data.repo;
  draw('hero.svg');
  generator();
}

main();
