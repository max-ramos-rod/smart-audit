/**
 * useInspectionSwipe.ts
 * ──────────────────────────────────────────────────────────────────────────
 * Gerencia os gestos de swipe do modo cartão (touch + mouse).
 * Swipe direita → Conforme; swipe esquerda → Não conforme + justificativa.
 *
 * USO em SubmissionDetailView:
 *
 *   const {
 *     swipeDeltaX, isSwiping, swipeExiting,
 *     cardSwipeStyle, rightIndicatorOpacity, leftIndicatorOpacity,
 *     onTouchStart, onTouchMove, onTouchEnd,
 *   } = useInspectionSwipe({
 *     getCurrentInstanceKey: () => inspKey.value,
 *     onConformeSwipe:       (key) => setConformityCard(key, 'conforme'),
 *     onNaoConformeSwipe:    (key) => setNaoConformeCard(key),
 *   })
 */
import { computed, ref } from 'vue'

interface SwipeHandlers {
  /** Retorna a instanceKey do campo atualmente exibido no cartão */
  getCurrentInstanceKey: () => string
  /** Chamado quando swipe para direita (≥80px) */
  onConformeSwipe: (instanceKey: string) => void
  /** Chamado quando swipe para esquerda (≤-80px) */
  onNaoConformeSwipe: (instanceKey: string) => void
}

export function useInspectionSwipe(handlers: SwipeHandlers) {
  const swipeDeltaX = ref(0)
  const swipeStartX = ref(0)
  const isSwiping = ref(false)
  const swipeExiting = ref<'left' | 'right' | null>(null)

  // ── Computed ──────────────────────────────────────────────────────────────

  /** Estilo CSS dinâmico do cartão (transform + opacity durante/após o swipe). */
  const cardSwipeStyle = computed(() => {
    if (!isSwiping.value && swipeDeltaX.value === 0) {
      if (swipeExiting.value === 'right') {
        return {
          transform: 'translateX(120%) rotate(12deg)',
          opacity: '0',
          transition: 'transform .22s ease, opacity .22s ease',
        }
      }
      if (swipeExiting.value === 'left') {
        return {
          transform: 'translateX(-120%) rotate(-12deg)',
          opacity: '0',
          transition: 'transform .22s ease, opacity .22s ease',
        }
      }
      return {}
    }
    const rotate = (swipeDeltaX.value / 400) * 12
    const opacity = Math.max(0.5, 1 - Math.abs(swipeDeltaX.value) / 400)
    return {
      transform: `translateX(${swipeDeltaX.value}px) rotate(${rotate}deg)`,
      opacity: String(opacity),
      transition: isSwiping.value ? 'none' : 'transform .22s ease, opacity .22s ease',
    }
  })

  /** Opacidade do indicador "Conforme" (lado direito). */
  const rightIndicatorOpacity = computed(() => Math.min(1, Math.max(0, swipeDeltaX.value / 100)))

  /** Opacidade do indicador "Não conforme" (lado esquerdo). */
  const leftIndicatorOpacity = computed(() => Math.min(1, Math.max(0, -swipeDeltaX.value / 100)))

  // ── Handlers de touch ─────────────────────────────────────────────────────

  function onTouchStart(e: TouchEvent) {
    swipeStartX.value = e.touches[0].clientX
    isSwiping.value = true
    swipeDeltaX.value = 0
  }

  function onTouchMove(e: TouchEvent) {
    if (!isSwiping.value) return
    swipeDeltaX.value = e.touches[0].clientX - swipeStartX.value
  }

  function onTouchEnd() {
    if (!isSwiping.value) return
    isSwiping.value = false

    const key = handlers.getCurrentInstanceKey()
    const delta = swipeDeltaX.value
    swipeDeltaX.value = 0

    if (!key || Math.abs(delta) < 80) return

    if (delta > 0) {
      handlers.onConformeSwipe(key)
    } else {
      handlers.onNaoConformeSwipe(key)
    }
  }

  return {
    swipeDeltaX,
    isSwiping,
    swipeExiting,
    cardSwipeStyle,
    rightIndicatorOpacity,
    leftIndicatorOpacity,
    onTouchStart,
    onTouchMove,
    onTouchEnd,
  }
}
