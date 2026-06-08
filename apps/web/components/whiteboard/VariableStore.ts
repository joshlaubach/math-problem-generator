// Reactive variable store for slider → axes binding.
// Module-level singleton: one store per browser page.

type Listener = () => void

const vars = new Map<string, number>()
const subs = new Map<string, Set<Listener>>()

export const variableStore = {
  set(name: string, value: number) {
    vars.set(name, value)
    subs.get(name)?.forEach(fn => fn())
  },

  get(name: string, fallback = 0): number {
    return vars.get(name) ?? fallback
  },

  all(): Record<string, number> {
    return Object.fromEntries(vars)
  },

  subscribe(name: string, fn: Listener): () => void {
    if (!subs.has(name)) subs.set(name, new Set())
    subs.get(name)!.add(fn)
    return () => { subs.get(name)?.delete(fn) }
  },

  clear() {
    vars.clear()
    subs.clear()
  },
}
