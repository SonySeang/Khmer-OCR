export function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

export function formatNumber(n) {
  return n.toLocaleString()
}

export function capitalize(s) {
  if (!s) return '—'
  return s.charAt(0).toUpperCase() + s.slice(1)
}

export function mode(arr) {
  const counts = {}
  arr.forEach(v => (counts[v] = (counts[v] || 0) + 1))
  return Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] || '—'
}
