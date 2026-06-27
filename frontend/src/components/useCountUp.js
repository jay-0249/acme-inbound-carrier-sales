import { useEffect, useRef, useState } from 'react'

const prefersReducedMotion = () =>
  typeof window !== 'undefined' &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches

export function useCountUp(target, duration = 600) {
  const [value, setValue] = useState(prefersReducedMotion() ? target : 0)
  const startRef = useRef(null)
  const rafRef   = useRef(null)

  useEffect(() => {
    if (prefersReducedMotion()) { setValue(target); return }
    const start = performance.now()
    startRef.current = start

    const tick = (now) => {
      const elapsed = now - start
      const progress = Math.min(elapsed / duration, 1)
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3)
      setValue(target * eased)
      if (progress < 1) rafRef.current = requestAnimationFrame(tick)
    }

    rafRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(rafRef.current)
  }, [target, duration])

  return value
}
