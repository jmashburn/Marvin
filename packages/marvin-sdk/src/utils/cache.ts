/**
 * Simple in-memory cache for SDK data
 */

interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

export class MarvinCache {
  private cache = new Map<string, CacheEntry<any>>();

  constructor(private duration: number = 5 * 60 * 1000) {}

  get<T>(key: string): T | undefined {
    const entry = this.cache.get(key);
    if (!entry) return undefined;

    const age = Date.now() - entry.timestamp;
    if (age > this.duration) {
      this.cache.delete(key);
      return undefined;
    }

    return entry.data as T;
  }

  set<T>(key: string, data: T): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
    });
  }

  has(key: string): boolean {
    return this.get(key) !== undefined;
  }

  clear(): void {
    this.cache.clear();
  }

  delete(key: string): void {
    this.cache.delete(key);
  }
}
