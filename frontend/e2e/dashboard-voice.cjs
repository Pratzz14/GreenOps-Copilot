/* Drive the real browser recorder with a deterministic microphone stream. */
const { expect: playwrightExpect } = require('@playwright/test');
const assert = require('node:assert/strict');
const path = require('node:path');

const expect = playwrightExpect.configure({ timeout: 15000 });
const api = '**/api/v1/dashboard/chat';
const questions = ['Which tool cost the most?', 'How did development compare?'];
const answers = ['Production spending was CHF 87,260.', 'Development spending was CHF 38,282.'];

function narration() {
  const samples = 16_000 * 3;
  const wav = Buffer.alloc(44 + samples * 2);
  wav.write('RIFF');
  wav.writeUInt32LE(wav.length - 8, 4);
  wav.write('WAVEfmt ', 8);
  wav.writeUInt32LE(16, 16);
  wav.writeUInt16LE(1, 20);
  wav.writeUInt16LE(1, 22);
  wav.writeUInt32LE(16_000, 24);
  wav.writeUInt32LE(32_000, 28);
  wav.writeUInt16LE(2, 32);
  wav.writeUInt16LE(16, 34);
  wav.write('data', 36);
  wav.writeUInt32LE(samples * 2, 40);
  for (let index = 0; index < samples; index += 1) {
    wav.writeInt16LE(Math.round(1500 * Math.sin(index * 2 * Math.PI * 420 / 16_000)), 44 + index * 2);
  }
  return wav;
}

const wave = narration();
const answerWithSources = answer => ({
  answer,
  sources: [{ layer: 'Gold', dataset: 'summary', scope: 'Baseline', url: '/data-explorer', rows: [{ cost: 38282 }] }],
});

async function openChat(browser, url, viewport) {
  const page = await browser.newPage({ viewport, isMobile: viewport.width < 600, hasTouch: viewport.width < 600 });
  await page.addInitScript(() => {
    const browserVoice = { denied: false, blocked: false, gain: null, context: null, track: null };
    window.browserVoice = browserVoice;
    Object.defineProperty(navigator, 'mediaDevices', { value: {
      async getUserMedia() {
        if (browserVoice.denied) throw new DOMException('Denied', 'NotAllowedError');
        const context = new AudioContext();
        const destination = context.createMediaStreamDestination();
        const oscillator = context.createOscillator();
        const gain = context.createGain();
        gain.gain.value = 0;
        oscillator.frequency.value = 260;
        oscillator.connect(gain).connect(destination);
        oscillator.start();
        const [track] = destination.stream.getAudioTracks();
        const stop = track.stop.bind(track);
        track.stop = () => {
          const stopped = Number(sessionStorage.getItem('dashboard-test-microphones-stopped') ?? 0);
          sessionStorage.setItem('dashboard-test-microphones-stopped', String(stopped + 1));
          stop();
          void context.close();
        };
        Object.assign(browserVoice, { track, gain, context });
        await context.resume();
        return destination.stream;
      },
    } });
    const play = HTMLMediaElement.prototype.play;
    HTMLMediaElement.prototype.play = function () {
      if (browserVoice.blocked) return Promise.reject(new DOMException('Autoplay blocked', 'NotAllowedError'));
      return play.call(this);
    };
  });
  await page.route(api + '/status', route => route.fulfill({ json: { configured: true, voice_configured: true } }));
  await page.goto(url + '/dashboard');
  await expect(page).toHaveTitle(/GreenOps/);
  await expect(page.getByRole('region', { name: 'Dashboard filters' })).toBeVisible();
  const open = () => page.getByRole('button', { name: 'Ask GreenOps', exact: true }).click();
  await open();
  const chat = page.getByRole('complementary', { name: 'Ask GreenOps' });
  await expect(chat.getByRole('button', { name: 'Start voice' })).toBeVisible();
  const tap = label => chat.getByRole('button', { name: label, exact: true }).click();
  const status = label => expect(chat.getByRole('status').filter({ hasText: label })).toBeVisible();
  const isCapturing = () => page.evaluate(() => window.browserVoice.track?.enabled ?? false);
  const say = (milliseconds = 440) => page.evaluate(duration => {
    const { context, gain } = window.browserVoice;
    const now = context.currentTime;
    gain.gain.cancelScheduledValues(now);
    gain.gain.setValueAtTime(0, now);
    gain.gain.setValueAtTime(0.16, now + 0.04);
    gain.gain.setValueAtTime(0, now + 0.04 + duration / 1000);
  }, milliseconds);
  return { page, chat, open, tap, status, isCapturing, say };
}

function checkRecording(clip) {
  assert.equal(clip.toString('ascii', 0, 4), 'RIFF');
  assert.equal(clip.readUInt32LE(24), 16_000);
  const frames = clip.readUInt32LE(40) / 2;
  assert.ok(frames > 16_000 && frames < 32_000);
  let onset = 0;
  while (onset < frames && Math.abs(clip.readInt16LE(44 + 2 * onset)) < 100) onset += 1;
  assert.ok(onset >= 1600 && onset <= 5000, `Expected a short pre-roll, measured ${onset / 16} ms`);
}

async function verifyConversation(browser, url, viewport) {
  const { page, chat, tap, status, isCapturing, say } = await openChat(browser, url, viewport);
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => {
    if (['warning', 'error'].includes(message.type())) errors.push(message.text());
  });
  const clips = [];
  const messages = [];
  const speeches = [];
  let releaseTranscript;
  let releaseAnswer;
  const run = await (await page.request.get(url + '/api/v1/runs/current')).json();
  await page.locator('#dashboard-metric').selectOption('energy');
  await page.route(api + '/transcribe', async route => {
    const clip = route.request().postDataBuffer();
    checkRecording(clip);
    clips.push(clip);
    if (clips.length === 1) await new Promise(resolve => { releaseTranscript = resolve; });
    await route.fulfill({ json: { text: questions[clips.length - 1] } });
  });
  await page.route(api, async route => {
    const message = route.request().postDataJSON();
    messages.push(message);
    if (messages.length === 1) await new Promise(resolve => { releaseAnswer = resolve; });
    await route.fulfill({ json: answerWithSources(answers[messages.length - 1] ?? 'Typed response.') });
  });
  await page.route(api + '/speech', route => {
    speeches.push(route.request().postDataJSON().text);
    return route.fulfill({ contentType: 'audio/wav', body: wave });
  });

  await tap('Start voice');
  await status('Listening');
  await page.waitForTimeout(950);
  assert.equal(clips.length, 0, 'Silence should not be submitted');
  await say();
  await status('Transcribing');
  assert.equal(await isCapturing(), false);
  await expect.poll(() => Boolean(releaseTranscript)).toBe(true);
  releaseTranscript();
  await status('Getting answer');
  await expect(chat.getByText(questions[0], { exact: false })).toBeVisible();
  await expect.poll(() => Boolean(releaseAnswer)).toBe(true);
  releaseAnswer();
  await status('Speaking');
  await expect(chat.getByText('AI-generated audio')).toBeVisible();
  assert.equal(await isCapturing(), false);
  await say(360);
  await page.waitForTimeout(1200);
  assert.equal(clips.length, 1, 'Playback must not produce a second transcript');
  await status('Listening');
  assert.equal(await isCapturing(), true);
  await page.waitForTimeout(320);
  await say();
  await status('Speaking');
  await expect(chat.getByText(answers[1])).toBeVisible();
  await expect(chat.getByRole('button', { name: 'End voice' })).toBeInViewport();
  await expect(chat.getByLabel('Your question')).toBeInViewport();
  if (process.env.VOICE_SCREENSHOT_DIR) {
    await page.screenshot({ path: path.join(process.env.VOICE_SCREENSHOT_DIR, `greenops-voice-${viewport.width}.png`) });
  }
  await tap('Interrupt');
  await status('Listening');
  assert.equal(await isCapturing(), true);
  assert.equal(messages.length, 2);
  assert.deepEqual(messages.map(message => message.question), questions);
  assert.ok(messages.every(message => message.run_id === run.run_id && message.filters.metric === 'energy'));
  assert.deepEqual(messages[1].history, [{ question: questions[0], answer: answers[0], scopes: ['Baseline'] }]);
  assert.deepEqual(speeches, answers);
  await tap('End voice');
  assert.equal(await page.evaluate(() => window.browserVoice.track.readyState), 'ended');
  await chat.getByLabel('Your question').fill('A typed question');
  await tap('Send');
  await expect(chat.getByText('Typed response.')).toBeVisible();
  assert.equal(speeches.length, 2, 'Typed replies should stay quiet');
  await tap('Listen');
  await status('Speaking');
  assert.equal(speeches.at(-1), 'Typed response.');
  await tap('Stop audio');
  await expect(chat.getByRole('button', { name: 'Start voice' })).toBeVisible();
  await tap('Clear chat');
  await tap('Which tools cost the most?');
  await expect(chat.getByText('Typed response.')).toBeVisible();
  await expect(chat.getByRole('button', { name: 'Listen', exact: true })).toBeVisible();
  assert.equal(speeches.length, 3, 'Starter replies should stay quiet');
  assert.deepEqual(errors, []);
  await page.close();
}

async function verifyRecovery(browser, url) {
  const { page, chat, open, tap, status, isCapturing, say } = await openChat(browser, url, { width: 390, height: 844 });
  let transcriptions = 0;
  let replies = 0;
  let speeches = 0;
  let firstClip;
  let gated;
  let release;
  const late = new Promise(resolve => { release = resolve; });
  await page.route(api + '/transcribe', async route => {
    transcriptions += 1;
    const clip = route.request().postDataBuffer();
    if (transcriptions === 1) {
      firstClip = clip;
      await route.fulfill({ status: 502, json: { detail: 'Provider failed.' } });
    } else if (transcriptions === 2) {
      assert.deepEqual(clip, firstClip);
      await route.fulfill({ json: { text: 'x'.repeat(2001) } });
    } else {
      await route.fulfill({ json: { text: questions[0] } });
    }
  });
  await page.route(api, route => {
    replies += 1;
    return route.fulfill({ json: answerWithSources(answers[0]) });
  });
  await page.route(api + '/speech', async route => {
    speeches += 1;
    if (speeches === 1) {
      await route.fulfill({ status: 502, json: { detail: 'Provider failed.' } });
    } else if (speeches === 3) {
      gated = true;
      await late;
      await route.fulfill({ contentType: 'audio/wav', body: wave }).catch(() => {});
    } else {
      await route.fulfill({ contentType: 'audio/wav', body: wave });
    }
  });
  await page.evaluate(() => { window.browserVoice.denied = true; });
  await tap('Start voice');
  await expect(chat.getByRole('alert')).toHaveText('Allow microphone access to use voice.');
  await tap('Type instead');
  await expect(chat.getByLabel('Your question')).toBeFocused();
  await page.evaluate(() => { window.browserVoice.denied = false; });
  await tap('Start voice');
  await status('Listening');
  await say();
  await expect(chat.getByRole('alert')).toHaveText('We couldn’t transcribe your recording.');
  assert.equal(replies, 0);
  await tap('Retry transcription');
  await expect(chat.getByRole('alert')).toHaveText('Try a shorter question.');
  assert.equal(replies, 0);
  await tap('Try again');
  await status('Listening');
  await say();
  await expect(chat.getByRole('alert')).toHaveText('We couldn’t play this answer.');
  await expect(chat.getByText(answers[0])).toBeVisible();
  await chat.getByText('Gold · summary · Baseline').click();
  await expect(chat.getByRole('link', { name: 'Open Gold source' })).toBeVisible();
  await page.evaluate(() => { window.browserVoice.blocked = true; });
  await tap('Retry playback');
  await expect(chat.getByRole('alert')).toHaveText('Tap to play the answer.');
  assert.equal(await isCapturing(), false);
  await page.evaluate(() => { window.browserVoice.blocked = false; });
  await tap('Play answer');
  await status('Speaking');
  assert.equal(replies, 1);
  assert.equal(speeches, 2, 'Autoplay recovery must reuse the downloaded narration');
  await tap('Interrupt');
  await status('Listening');
  await say();
  await expect.poll(() => gated).toBe(true);
  await tap('Close chat');
  assert.equal(await page.evaluate(() => window.browserVoice.track.readyState), 'ended');
  release();
  await open();
  await expect(chat.getByRole('button', { name: 'Start voice' })).toBeVisible();
  assert.equal(await page.evaluate(() => window.browserVoice.track.readyState), 'ended');
  assert.equal(speeches, 3);
  await tap('Start voice');
  await status('Listening');
  await tap('Clear chat');
  await expect(chat.getByRole('log')).toBeEmpty();
  assert.equal(await page.evaluate(() => window.browserVoice.track.readyState), 'ended');
  await tap('Start voice');
  await status('Listening');
  const stoppedTracks = () => page.evaluate(() => Number(sessionStorage.getItem('dashboard-test-microphones-stopped') ?? 0));
  const beforeNavigation = await stoppedTracks();
  await page.getByRole('link', { name: 'Data Explorer', exact: true }).first().click();
  await expect(chat).toHaveCount(0);
  await expect.poll(stoppedTracks).toBe(beforeNavigation + 1);
  await page.getByRole('link', { name: 'Dashboard', exact: true }).first().click();
  await open();
  const current = await (await page.request.get(url + '/api/v1/runs/current')).json();
  const publishedRun = 'f'.repeat(current.run_id.length);
  await page.route(`**/api/v1/runs/${publishedRun}/**`, route => route.continue({
    url: route.request().url().replace(publishedRun, current.run_id),
  }));
  await tap('Start voice');
  await status('Listening');
  await page.route('**/api/v1/runs/current', route => route.fulfill({ json: { ...current, run_id: publishedRun } }));
  await expect(chat).toBeHidden();
  assert.equal(await page.evaluate(() => window.browserVoice.track.readyState), 'ended');
  await page.close();
}

module.exports = { verifyConversation, verifyRecovery };
