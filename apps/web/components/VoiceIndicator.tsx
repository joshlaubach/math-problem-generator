'use client'

/**
 * VoiceIndicator — organic blob animation reflecting the voice agent's state.
 *
 * States:
 *   recording    → blobby equalizer (student speaking)
 *   transcribing → pendulum goo (processing speech)
 *   thinking     → swirl cluster (tutor thinking)
 *   speaking     → inkblot satellites (tutor speaking)
 *   idle         → tadpole chaser (voice mode armed, waiting)
 *
 * Pure CSS; monochrome via currentColor. Designed at 200x200 and scaled.
 */

import React from 'react'

export type VoiceIndicatorState = 'idle' | 'recording' | 'transcribing' | 'thinking' | 'speaking'

const STATE_LABEL: Record<VoiceIndicatorState, string> = {
  idle: 'Voice mode ready',
  recording: 'Listening',
  transcribing: 'Transcribing',
  thinking: 'Tutor is thinking',
  speaking: 'Tutor is speaking',
}

const CSS = `
@keyframes vi-spin{to{transform:rotate(360deg)}}
@keyframes vi-m1{0%,100%{border-radius:60% 40% 35% 65%/55% 35% 65% 45%}25%{border-radius:40% 60% 65% 35%/45% 60% 40% 55%}50%{border-radius:35% 65% 45% 55%/60% 40% 55% 45%}75%{border-radius:55% 45% 60% 40%/40% 65% 35% 60%}}
@keyframes vi-eq{0%,100%{height:32px}50%{height:84px}}
@keyframes vi-pop{0%,100%{transform:translate(0,0) scale(.15)}50%{transform:translate(var(--dx),var(--dy)) scale(1)}}
@keyframes vi-pnd{0%,100%{transform:translateX(-50px)}50%{transform:translateX(50px)}}
.vi-g{position:absolute;inset:0;filter:url(#vi-goo)}
.vi-d{position:absolute;background:currentColor;border-radius:50%}
.vi-ctr{position:absolute;left:50%;top:50%;width:0;height:0;animation:vi-spin linear infinite}
.vi-p{width:24px;background:currentColor;border-radius:12px;animation:vi-eq ease-in-out infinite}
`

function Equalizer() {
  return (
    <div className="vi-g" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10 }}>
      <div className="vi-p" style={{ animationDuration: '1.2s' }} />
      <div className="vi-p" style={{ animationDuration: '1.4s', animationDelay: '-.5s' }} />
      <div className="vi-p" style={{ animationDuration: '1.1s', animationDelay: '-.2s' }} />
      <div className="vi-p" style={{ animationDuration: '1.5s', animationDelay: '-.8s' }} />
    </div>
  )
}

function Pendulum() {
  return (
    <div className="vi-g">
      <div className="vi-d" style={{ width: 32, height: 32, left: '50%', top: '50%', margin: -16, animation: 'vi-pnd 1.5s ease-in-out infinite' }} />
      <div className="vi-d" style={{ width: 22, height: 22, left: '50%', top: '50%', margin: -11, animation: 'vi-pnd 1.5s ease-in-out -1.38s infinite' }} />
      <div className="vi-d" style={{ width: 14, height: 14, left: '50%', top: '50%', margin: -7, animation: 'vi-pnd 1.5s ease-in-out -1.28s infinite' }} />
    </div>
  )
}

function Swirl() {
  const dots: Array<[number, number, string, boolean]> = [
    [26, 11, '1.8s', false],
    [22, 25, '2.6s', false],
    [18, 39, '3.4s', true],
    [20, 20, '2.2s', true],
    [14, 49, '4s', false],
  ]
  return (
    <div className="vi-g">
      {dots.map(([size, radius, dur, reverse], i) => (
        <div key={i} className="vi-ctr" style={{ animationDuration: dur, animationDirection: reverse ? 'reverse' : undefined }}>
          <div className="vi-d" style={{ width: size, height: size, left: radius, top: -size / 2 }} />
        </div>
      ))}
    </div>
  )
}

function Inkblot() {
  const sats: Array<[string, string, string]> = [
    ['48px', '-30px', '0s'],
    ['-46px', '-36px', '.7s'],
    ['42px', '40px', '1.4s'],
    ['-44px', '34px', '2.1s'],
  ]
  return (
    <div className="vi-g">
      <div style={{
        position: 'absolute', width: 72, height: 72, left: '50%', top: '50%', margin: -36,
        background: 'currentColor', animation: 'vi-m1 4s ease-in-out infinite',
      }} />
      {sats.map(([dx, dy, delay], i) => (
        <div
          key={i}
          className="vi-d"
          style={{
            width: 20, height: 20, left: '50%', top: '50%', margin: -10,
            animation: `vi-pop 2.8s ease-in-out ${delay} infinite`,
            '--dx': dx, '--dy': dy,
          } as React.CSSProperties}
        />
      ))}
    </div>
  )
}

function Tadpole() {
  const dots: Array<[number, number, string]> = [
    [22, 45, '0s'], [19, 47, '-.1s'], [16, 48, '-.2s'],
    [13, 50, '-.3s'], [10, 51, '-.4s'], [8, 52, '-.5s'],
  ]
  return (
    <div className="vi-g">
      {dots.map(([size, radius, delay], i) => (
        <div key={i} className="vi-ctr" style={{ animationDuration: '2.4s', animationDelay: delay }}>
          <div className="vi-d" style={{ width: size, height: size, left: radius, top: -size / 2 }} />
        </div>
      ))}
    </div>
  )
}

export function VoiceIndicator({
  state,
  size = 48,
  color = 'var(--text)',
}: {
  state: VoiceIndicatorState
  size?: number
  color?: string
}) {
  return (
    <div
      role="status"
      aria-label={STATE_LABEL[state]}
      style={{ width: size, height: size, position: 'relative', color, flexShrink: 0 }}
    >
      <style>{CSS}</style>
      <svg width="0" height="0" style={{ position: 'absolute' }} aria-hidden="true">
        <defs>
          <filter id="vi-goo">
            <feGaussianBlur in="SourceGraphic" stdDeviation="7" result="b" />
            <feColorMatrix in="b" values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 19 -8" />
          </filter>
        </defs>
      </svg>
      <div style={{
        position: 'absolute', left: '50%', top: '50%', width: 200, height: 200,
        transform: `translate(-50%,-50%) scale(${size / 200})`,
      }}>
        {state === 'recording' && <Equalizer />}
        {state === 'transcribing' && <Pendulum />}
        {state === 'thinking' && <Swirl />}
        {state === 'speaking' && <Inkblot />}
        {state === 'idle' && <Tadpole />}
      </div>
    </div>
  )
}
