import { ReactLenis } from "lenis/react"
import "lenis/dist/lenis.css"

export function SmoothScroll({ children }) {
  return <ReactLenis root={true}>{children}</ReactLenis>
}