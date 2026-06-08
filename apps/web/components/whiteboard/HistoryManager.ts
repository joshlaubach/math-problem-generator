// Ring-buffer undo/redo manager. Stores serialised JSON strings to avoid
// holding references to live Fabric objects.

export class HistoryManager {
  private stack: string[] = []
  private idx = -1
  private readonly limit: number

  constructor(limit = 50) {
    this.limit = limit
  }

  push(state: object): void {
    // Drop everything after the current cursor
    this.stack = this.stack.slice(0, this.idx + 1)
    this.stack.push(JSON.stringify(state))
    // Enforce capacity
    if (this.stack.length > this.limit) {
      this.stack.shift()
    }
    this.idx = this.stack.length - 1
  }

  undo(): string | null {
    if (this.idx <= 0) return null
    this.idx--
    return this.stack[this.idx]
  }

  redo(): string | null {
    if (this.idx >= this.stack.length - 1) return null
    this.idx++
    return this.stack[this.idx]
  }

  canUndo(): boolean { return this.idx > 0 }
  canRedo(): boolean { return this.idx < this.stack.length - 1 }
  current(): string | null { return this.stack[this.idx] ?? null }

  clear(): void {
    this.stack = []
    this.idx = -1
  }
}
