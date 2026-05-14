'use client';

import { useState } from 'react';
import { MathText } from '@/components/MathText';
import { MathInput } from '@/components/MathInput';

const EXAMPLES = [
  { label: 'Quadratic formula', latex: 'x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}' },
  { label: 'Gaussian integral', latex: '\\int_{-\\infty}^{\\infty} e^{-x^2}\\,dx = \\sqrt{\\pi}' },
  { label: "Euler's identity", latex: 'e^{i\\pi} + 1 = 0' },
  { label: 'Pythagorean theorem', latex: 'a^2 + b^2 = c^2' },
];

export default function TestMathPage() {
  const [inputLatex, setInputLatex] = useState('\\frac{x+1}{2}');

  return (
    <main className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-2xl mx-auto space-y-10">
        <header>
          <h1 className="text-3xl font-bold text-gray-900">Phase 5 — Math Rendering Test</h1>
          <p className="mt-1 text-gray-500 text-sm">
            KaTeX block/inline rendering + MathLive round-trip
          </p>
        </header>

        {/* Block rendering */}
        <section className="bg-white rounded-2xl shadow-sm p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-800">Block KaTeX</h2>
          {EXAMPLES.map((ex) => (
            <div key={ex.label} className="border-b border-gray-100 pb-4 last:border-none last:pb-0">
              <p className="text-xs text-gray-400 mb-1">{ex.label}</p>
              <MathText latex={ex.latex} />
            </div>
          ))}
        </section>

        {/* Inline rendering */}
        <section className="bg-white rounded-2xl shadow-sm p-6 space-y-2">
          <h2 className="text-lg font-semibold text-gray-800">Inline KaTeX</h2>
          <p className="text-gray-700 leading-relaxed">
            The slope of a line is{' '}
            <MathText latex="m = \frac{\Delta y}{\Delta x}" inline />, and the
            area of a circle is{' '}
            <MathText latex="A = \pi r^2" inline />.
          </p>
        </section>

        {/* MathLive round-trip */}
        <section className="bg-white rounded-2xl shadow-sm p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-800">MathLive Input Round-trip</h2>
          <p className="text-sm text-gray-500">
            Type math in the field below. The LaTeX string is echoed live and
            re-rendered by KaTeX.
          </p>

          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Input field (MathLive)
            </label>
            <MathInput
              value={inputLatex}
              onChange={setInputLatex}
              placeholder="Type math here…"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">
              LaTeX string
            </label>
            <code className="block bg-gray-100 text-gray-800 text-sm rounded px-3 py-2 font-mono break-all">
              {inputLatex || <span className="text-gray-400 italic">empty</span>}
            </code>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">
              KaTeX render
            </label>
            <div className="border border-gray-200 rounded-lg px-4 py-2 min-h-12">
              {inputLatex ? (
                <MathText latex={inputLatex} />
              ) : (
                <span className="text-gray-400 italic text-sm">nothing to render</span>
              )}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
