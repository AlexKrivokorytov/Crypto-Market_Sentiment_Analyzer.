import type { RouteAssetId } from '@/types/market'

/** Canonical display order for crypto assets across all dashboard components. */
export const CRYPTO_ASSET_ORDER: RouteAssetId[] = [
  'BTC', 'ETH', 'SOL', 'TON', 'XRP', 'ADA',
  'DOGE', 'DOT', 'LINK', 'AVAX', 'MATIC', 'SHIB', 'LTC', 'UNI', 'NEAR', 'ATOM',
]

/** Assets displayed in the sentiment heatmap (subset of the above). */
export const HEATMAP_ASSET_IDS: RouteAssetId[] = [
  'BTC', 'ETH', 'TON', 'SOL', 'XRP', 'ADA',
]

/** The asset the router redirects to when no valid ID is present. */
export const DEFAULT_ASSET: RouteAssetId = 'BTC'
