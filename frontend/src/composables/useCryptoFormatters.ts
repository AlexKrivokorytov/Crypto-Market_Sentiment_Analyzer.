/**
 * Crypto-native formatting utilities.
 *
 * All functions are pure, side-effect-free, and accept only explicit types —
 * no `any`, no implicit coercions.
 *
 * Usage:
 *   import { formatPrice, formatVolume, formatVaderScore, formatRelativeTime,
 *            getAssetBrandColor, getAssetGradient } from '@/composables/useCryptoFormatters'
 */

import type { RouteAssetId } from '@/types/market'

// ─── Asset Brand Colour Registry ───────────────────────────────────────────

/** Canonical brand hex colour for each tracked asset. */
const ASSET_BRAND_COLORS: Readonly<Record<RouteAssetId, string>> = {
  BTC: '#F7931A',  // Bitcoin orange
  ETH: '#627EEA',  // Ethereum blue-violet
  TON: '#0098EA',  // TON sky blue
  SOL: '#9945FF',  // Solana purple
  XRP: '#00AAE4',  // Ripple cyan
  ADA: '#3CC8C8',  // Cardano teal
  AAPL: '#A2AAAD', // Apple silver
}

/** Two-stop CSS linear-gradient for card tinted backgrounds. */
const ASSET_GRADIENTS: Readonly<Record<RouteAssetId, string>> = {
  BTC:  'linear-gradient(135deg, rgba(247, 147, 26, 0.12) 0%, rgba(247, 147, 26, 0.02) 100%)',
  ETH:  'linear-gradient(135deg, rgba(98,  126, 234, 0.12) 0%, rgba(98,  126, 234, 0.02) 100%)',
  TON:  'linear-gradient(135deg, rgba(0,  152, 234, 0.12) 0%, rgba(0,  152, 234, 0.02) 100%)',
  SOL:  'linear-gradient(135deg, rgba(153, 69, 255, 0.12) 0%, rgba(153, 69, 255, 0.02) 100%)',
  XRP:  'linear-gradient(135deg, rgba(0,  170, 228, 0.12) 0%, rgba(0,  170, 228, 0.02) 100%)',
  ADA:  'linear-gradient(135deg, rgba(60,  200, 200, 0.12) 0%, rgba(60,  200, 200, 0.02) 100%)',
  AAPL: 'linear-gradient(135deg, rgba(162, 170, 173, 0.10) 0%, rgba(162, 170, 173, 0.02) 100%)',
}

/**
 * Returns the canonical brand hex colour for a tracked asset.
 *
 * @param symbol - One of the 7 tracked asset tickers.
 * @returns Hex colour string, e.g. '#F7931A'.
 */
export function getAssetBrandColor(symbol: RouteAssetId): string {
  return ASSET_BRAND_COLORS[symbol]
}

/**
 * Returns a two-stop CSS gradient string tinted with the asset brand colour.
 * Suitable for `background` or `backgroundImage` inline styles.
 *
 * @param symbol - One of the 7 tracked asset tickers.
 * @returns CSS `linear-gradient(...)` string.
 */
export function getAssetGradient(symbol: RouteAssetId): string {
  return ASSET_GRADIENTS[symbol]
}

// ─── Price Formatting ───────────────────────────────────────────────────────

/**
 * Formats a USD price with smart decimal precision.
 *
 * Rules:
 * - price ≥ 1000   → 0 fractional digits, thousands separator  (e.g. $67,423)
 * - price ≥ 1      → 2 fractional digits                        (e.g. $182.45)
 * - price ≥ 0.01   → 4 fractional digits                        (e.g. $0.5812)
 * - price < 0.01   → 6 fractional digits                        (e.g. $0.000412)
 *
 * @param value  - Numeric USD price.
 * @param symbol - Optional asset ticker to tailor decimal behaviour (AAPL always 2dp).
 * @returns Locale-formatted string like '$67,423' or '$0.5812'.
 */
export function formatPrice(value: number, symbol?: RouteAssetId): string {
  if (!isFinite(value)) return '—'

  // Equities always show cents
  if (symbol === 'AAPL') {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value)
  }

  let fractionDigits: number
  if (value >= 1000) fractionDigits = 0
  else if (value >= 1) fractionDigits = 2
  else if (value >= 0.01) fractionDigits = 4
  else fractionDigits = 6

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  }).format(value)
}

/**
 * Formats a 24-hour percentage change with an explicit sign prefix.
 *
 * @param value - Float, e.g. 3.42 or -1.87.
 * @returns String like '+3.42%' or '-1.87%'.
 */
export function formatChange(value: number): string {
  if (!isFinite(value)) return '—'
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}

// ─── Volume / Market Cap Formatting ────────────────────────────────────────

/**
 * Formats a large USD volume into a compact human-readable string.
 *
 * Ranges:
 * - ≥ 1 000 000 000 → '$X.XXB'
 * - ≥ 1 000 000     → '$X.XXM'
 * - ≥ 1 000         → '$X.XXK'
 * - < 1 000         → '$X' (integer)
 *
 * @param value - Raw numeric volume in USD.
 * @returns Compact string like '$12.4B'.
 */
export function formatVolume(value: number): string {
  if (!isFinite(value) || value < 0) return '—'
  if (value >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(2)}B`
  if (value >= 1_000_000)     return `$${(value / 1_000_000).toFixed(2)}M`
  if (value >= 1_000)         return `$${(value / 1_000).toFixed(1)}K`
  return `$${Math.round(value)}`
}

// ─── Gas Price Formatting ───────────────────────────────────────────────────

/**
 * Formats a gas price in Gwei with consistent 2 decimal precision.
 * Returns '—' for non-applicable assets (e.g. AAPL, BTC).
 *
 * @param gwei   - Gas price in Gwei as a float.
 * @param symbol - Asset ticker; returns '—' for non-chain assets.
 * @returns Formatted string like '18.42 Gwei' or '—'.
 */
export function formatGasPrice(gwei: number, symbol: RouteAssetId): string {
  const onChainAssets: RouteAssetId[] = ['ETH', 'SOL', 'TON']
  if (!onChainAssets.includes(symbol)) return '—'
  if (!isFinite(gwei)) return '—'
  return `${gwei.toFixed(2)} Gwei`
}

// ─── VADER Score Formatting ─────────────────────────────────────────────────

/**
 * Formats a VADER compound score (range −1.0 to +1.0) with an explicit sign.
 *
 * @param score - Float in [−1.0, +1.0].
 * @returns String like '+0.72' or '−0.31' or '0.00'.
 */
export function formatVaderScore(score: number): string {
  if (!isFinite(score)) return '—'
  const clamped = Math.max(-1, Math.min(1, score))
  const sign = clamped > 0 ? '+' : ''
  return `${sign}${clamped.toFixed(2)}`
}

/**
 * Maps a 0–100 sentiment index back to the VADER compound scale (−1.0 to +1.0).
 *
 * Formula: compound = (index − 50) / 50
 *
 * @param index - Integer in [0, 100].
 * @returns Float in [−1.0, +1.0].
 */
export function sentimentIndexToVader(index: number): number {
  return Math.max(-1, Math.min(1, (index - 50) / 50))
}

/**
 * Maps a VADER compound score back to a 0–100 sentiment index.
 *
 * Formula: index = round((compound * 50) + 50)
 *
 * @param compound - Float in [−1.0, +1.0].
 * @returns Integer in [0, 100].
 */
export function vaderToSentimentIndex(compound: number): number {
  return Math.min(100, Math.max(0, Math.round(compound * 50 + 50)))
}

// ─── Relative Time ──────────────────────────────────────────────────────────

/**
 * Returns a concise relative-time label from an ISO 8601 string.
 *
 * Thresholds:
 * - < 60s   → 'just now'
 * - < 60m   → 'Xm ago'
 * - < 24h   → 'Xh ago'
 * - < 7d    → 'Xd ago'
 * - ≥ 7d    → locale date string (e.g. 'May 10')
 *
 * @param isoString - ISO 8601 timestamp string, e.g. '2026-05-28T20:00:00Z'.
 * @returns Human-readable relative label.
 */
export function formatRelativeTime(isoString: string): string {
  const date = new Date(isoString)
  if (isNaN(date.getTime())) return '—'

  const nowMs = Date.now()
  const diffMs = nowMs - date.getTime()
  const diffSec = Math.floor(diffMs / 1000)

  if (diffSec < 60)       return 'just now'
  if (diffSec < 3600)     return `${Math.floor(diffSec / 60)}m ago`
  if (diffSec < 86400)    return `${Math.floor(diffSec / 3600)}h ago`
  if (diffSec < 604800)   return `${Math.floor(diffSec / 86400)}d ago`

  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

// ─── Sentiment Label Helpers ────────────────────────────────────────────────

/**
 * Returns the Tailwind CSS utility class for a sentiment label's text colour.
 *
 * @param label - 'Bullish' | 'Bearish' | 'Neutral'.
 * @returns Tailwind class string.
 */
export function getSentimentTextClass(label: string): string {
  if (label === 'Bullish') return 'text-bullish'
  if (label === 'Bearish') return 'text-bearish'
  return 'text-neutral'
}

/**
 * Returns the Tailwind CSS utility class for a sentiment label's background badge.
 *
 * @param label - 'Bullish' | 'Bearish' | 'Neutral'.
 * @returns Tailwind class string for badge styling.
 */
export function getSentimentBadgeClass(label: string): string {
  if (label === 'Bullish') return 'bg-bullish/10 text-bullish border-bullish/30'
  if (label === 'Bearish') return 'bg-bearish/10 text-bearish border-bearish/30'
  return 'bg-neutral/10 text-neutral border-neutral/30'
}
