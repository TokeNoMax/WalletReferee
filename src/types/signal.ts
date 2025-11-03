export type RefStatus = 'ok' | 'degraded';
export type RefDecision = 'BUY' | 'SELL' | 'HOLD';

export interface SignalEntry {
  id: string;
  symbol: string;
  signal: RefDecision;
  confidence: number; // 0..1
  price?: number;
  reason?: string;
 : string;  // ISO
}

export interface SignalFile {
  version: '1';
  generatedAt: string; // ISO
  status: RefStatus;
  entries: SignalEntry[];
}
