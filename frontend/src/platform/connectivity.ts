export interface ConnectivityStatus {
  online: boolean
}

export type ConnectivityListener = (status: ConnectivityStatus) => void

const listeners = new Set<ConnectivityListener>()

let online = navigator.onLine

function setOnline(value: boolean): void {
  online = value
  const status: ConnectivityStatus = { online }
  for (const listener of listeners) listener(status)
}

window.addEventListener('online', () => setOnline(true))
window.addEventListener('offline', () => setOnline(false))

export function getConnectivityStatus(): ConnectivityStatus {
  return { online }
}

export function subscribeToConnectivity(listener: ConnectivityListener): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}
