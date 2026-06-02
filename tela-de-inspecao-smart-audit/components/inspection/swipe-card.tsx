'use client'

import { useState, useCallback, useRef } from 'react'
import { motion, useMotionValue, useTransform, PanInfo } from 'framer-motion'
import { Check, X, Camera, Mic, Video, FileText, ChevronDown, ChevronUp, Paperclip, Minus } from 'lucide-react'
import { useInspection } from './inspection-context'
import type { FormField, FieldValue } from '@/lib/types'
import { cn } from '@/lib/utils'

interface SwipeCardProps {
  field: FormField
  onSwipeComplete: (direction: 'left' | 'right' | 'na') => void
  isActive: boolean
}

export function SwipeCard({ field, onSwipeComplete, isActive }: SwipeCardProps) {
  const { 
    answers, 
    attachments, 
    pendingEvidences,
    addPendingEvidence,
    getFieldStatus 
  } = useInspection()
  
  const [showHelp, setShowHelp] = useState(false)
  const [showEvidenceMenu, setShowEvidenceMenu] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  
  const x = useMotionValue(0)
  const rotate = useTransform(x, [-200, 200], [-15, 15])
  const opacity = useTransform(x, [-200, -100, 0, 100, 200], [0.5, 1, 1, 1, 0.5])
  
  const rightIndicatorOpacity = useTransform(x, [0, 100], [0, 1])
  const leftIndicatorOpacity = useTransform(x, [-100, 0], [1, 0])
  
  const fieldAttachments = attachments.get(field.key) || []
  const fieldPendingEvidences = pendingEvidences.get(field.key) || []
  const evidenceCount = fieldAttachments.length + fieldPendingEvidences.length
  
  const status = getFieldStatus(field)
  const allowNa = field.config_json.allow_na === true
  const weight = field.config_json.weight ?? 1
  
  const constraintsRef = useRef(null)

  const handleDragEnd = useCallback((_: MouseEvent | TouchEvent | PointerEvent, info: PanInfo) => {
    setIsDragging(false)
    const threshold = 100
    
    if (info.offset.x > threshold) {
      onSwipeComplete('right')
    } else if (info.offset.x < -threshold) {
      setShowEvidenceMenu(true)
    }
  }, [onSwipeComplete])

  const handleAddEvidence = (type: 'photo' | 'video' | 'audio' | 'note') => {
    addPendingEvidence(field.key, {
      id: crypto.randomUUID(),
      type,
      content: type === 'note' ? '' : undefined,
      created_at: new Date().toISOString(),
    })
    setShowEvidenceMenu(false)
  }

  const handleMarkNonCompliant = () => {
    onSwipeComplete('left')
    setShowEvidenceMenu(false)
  }

  const handleMarkNa = () => {
    onSwipeComplete('na')
    setShowEvidenceMenu(false)
  }

  if (!isActive) return null

  // Para campos não-booleanos, mostrar card diferente
  if (field.field_type !== 'boolean') {
    return (
      <NonBooleanCard 
        field={field} 
        onComplete={() => onSwipeComplete('right')} 
      />
    )
  }

  return (
    <div ref={constraintsRef} className="relative w-full h-full flex items-center justify-center px-4">
      {/* Swipe Indicators */}
      <motion.div 
        className="absolute left-8 top-1/2 -translate-y-1/2 flex flex-col items-center gap-2 pointer-events-none"
        style={{ opacity: leftIndicatorOpacity }}
      >
        <div className="w-14 h-14 rounded-full bg-destructive flex items-center justify-center shadow-lg">
          <X className="w-7 h-7 text-destructive-foreground" />
        </div>
        <span className="text-xs font-medium text-destructive">Não Conforme</span>
      </motion.div>
      
      <motion.div 
        className="absolute right-8 top-1/2 -translate-y-1/2 flex flex-col items-center gap-2 pointer-events-none"
        style={{ opacity: rightIndicatorOpacity }}
      >
        <div className="w-14 h-14 rounded-full bg-success flex items-center justify-center shadow-lg">
          <Check className="w-7 h-7 text-success-foreground" />
        </div>
        <span className="text-xs font-medium text-success">Conforme</span>
      </motion.div>

      {/* Card */}
      <motion.div
        drag={!showEvidenceMenu ? "x" : false}
        dragConstraints={{ left: 0, right: 0 }}
        dragElastic={0.7}
        onDragStart={() => setIsDragging(true)}
        onDragEnd={handleDragEnd}
        style={{ x, rotate, opacity }}
        className={cn(
          "insp-card w-full max-w-md bg-card rounded-2xl shadow-xl border border-border overflow-hidden touch-pan-y",
          isDragging && "cursor-grabbing"
        )}
      >
        {/* Status Header */}
        <div className={cn(
          "insp-meta px-4 py-3 flex items-center justify-between",
          status === 'pending' && "bg-muted",
          status === 'compliant' && "bg-success/10",
          status === 'non_compliant' && "bg-destructive/10",
          status === 'na' && "bg-warning/10"
        )}>
          <div className="flex items-center gap-2">
            <span className="text-sm font-mono text-muted-foreground">{field.key}</span>
            {weight !== 1 && (
              <span className="px-1.5 py-0.5 text-xs bg-primary/10 text-primary rounded font-medium">
                Peso {weight}x
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {evidenceCount > 0 && (
              <span className="inline-flex items-center gap-1 px-2 py-1 bg-primary/10 text-primary text-xs font-medium rounded-full">
                <Paperclip className="w-3 h-3" />
                {evidenceCount}
              </span>
            )}
            <span className={cn(
              "px-2 py-1 text-xs font-medium rounded-full",
              status === 'pending' && "bg-pending text-pending-foreground",
              status === 'compliant' && "bg-success text-success-foreground",
              status === 'non_compliant' && "bg-destructive text-destructive-foreground",
              status === 'na' && "bg-warning text-warning-foreground"
            )}>
              {status === 'pending' && 'Pendente'}
              {status === 'compliant' && 'Conforme'}
              {status === 'non_compliant' && 'Não Conforme'}
              {status === 'na' && 'N/A'}
            </span>
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          <h3 className="text-lg font-semibold text-foreground leading-tight mb-3 text-balance">
            {field.label}
          </h3>
          
          {field.required && (
            <span className="inline-block px-2 py-0.5 text-xs bg-destructive/10 text-destructive rounded mb-4">
              Obrigatório
            </span>
          )}

          {/* Help Text Accordion - usando description ou config */}
          <div className="mt-4">
            <button
              onClick={() => setShowHelp(!showHelp)}
              className="flex items-center gap-2 text-sm text-primary font-medium touch-target"
            >
              {showHelp ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              Orientação
            </button>
            {showHelp && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="mt-2 p-3 bg-muted rounded-lg"
              >
                <p className="text-sm text-muted-foreground">
                  Verifique cuidadosamente este item conforme os critérios estabelecidos.
                  {allowNa && ' Este campo aceita marcação N/A (Não Aplicável).'}
                </p>
              </motion.div>
            )}
          </div>
        </div>

        {/* Swipe Hint */}
        <div className="px-6 pb-6 text-center">
          <p className="text-xs text-muted-foreground">
            ← Deslize para marcar · Deslize para aprovar →
          </p>
        </div>
      </motion.div>

      {/* Evidence Menu Modal */}
      {showEvidenceMenu && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="fixed inset-0 z-50 bg-foreground/50 flex items-end justify-center"
          onClick={() => setShowEvidenceMenu(false)}
        >
          <motion.div
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            className="w-full max-w-md bg-card rounded-t-2xl p-6 safe-area-bottom"
            onClick={e => e.stopPropagation()}
          >
            <div className="w-12 h-1 bg-muted rounded-full mx-auto mb-6" />
            
            <h3 className="text-lg font-semibold text-foreground mb-4">
              Registrar Não-Conformidade
            </h3>
            
            <div className="grid grid-cols-4 gap-4 mb-6">
              <button
                onClick={() => handleAddEvidence('photo')}
                className="flex flex-col items-center gap-2 p-4 rounded-xl bg-muted hover:bg-muted/80 transition-colors touch-target"
              >
                <Camera className="w-6 h-6 text-primary" />
                <span className="text-xs font-medium">Foto</span>
              </button>
              <button
                onClick={() => handleAddEvidence('video')}
                className="flex flex-col items-center gap-2 p-4 rounded-xl bg-muted hover:bg-muted/80 transition-colors touch-target"
              >
                <Video className="w-6 h-6 text-primary" />
                <span className="text-xs font-medium">Vídeo</span>
              </button>
              <button
                onClick={() => handleAddEvidence('audio')}
                className="flex flex-col items-center gap-2 p-4 rounded-xl bg-muted hover:bg-muted/80 transition-colors touch-target"
              >
                <Mic className="w-6 h-6 text-primary" />
                <span className="text-xs font-medium">Áudio</span>
              </button>
              <button
                onClick={() => handleAddEvidence('note')}
                className="flex flex-col items-center gap-2 p-4 rounded-xl bg-muted hover:bg-muted/80 transition-colors touch-target"
              >
                <FileText className="w-6 h-6 text-primary" />
                <span className="text-xs font-medium">Nota</span>
              </button>
            </div>

            <div className="flex flex-col gap-3">
              {allowNa && (
                <button
                  onClick={handleMarkNa}
                  className="w-full py-3 px-4 rounded-xl bg-warning text-warning-foreground font-medium touch-target flex items-center justify-center gap-2"
                >
                  <Minus className="w-5 h-5" />
                  Marcar como N/A
                </button>
              )}
              <div className="flex gap-3">
                <button
                  onClick={() => setShowEvidenceMenu(false)}
                  className="flex-1 py-3 px-4 rounded-xl border border-border text-foreground font-medium touch-target"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleMarkNonCompliant}
                  className="flex-1 py-3 px-4 rounded-xl bg-destructive text-destructive-foreground font-medium touch-target"
                >
                  Não Conforme
                </button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </div>
  )
}

// Componente para campos não-booleanos (text, number, select, date, photo, evidence)
function NonBooleanCard({ 
  field, 
  onComplete 
}: { 
  field: FormField
  onComplete: () => void 
}) {
  const { answers, setAnswer } = useInspection()
  const [localValue, setLocalValue] = useState<string>(
    answers[field.key]?.toString() ?? ''
  )

  const handleSave = () => {
    let value: FieldValue = localValue

    if (field.field_type === 'number') {
      value = parseFloat(localValue) || null
    } else if (field.field_type === 'select') {
      value = { option: localValue }
    }

    setAnswer(field.key, value)
    onComplete()
  }

  return (
    <div className="w-full max-w-md mx-4">
      <div className="insp-card bg-card rounded-2xl shadow-xl border border-border overflow-hidden">
        <div className="insp-meta px-4 py-3 bg-muted">
          <span className="text-sm font-mono text-muted-foreground">{field.key}</span>
        </div>

        <div className="p-6">
          <h3 className="text-lg font-semibold text-foreground leading-tight mb-4 text-balance">
            {field.label}
          </h3>

          {field.field_type === 'text' && (
            <textarea
              value={localValue}
              onChange={(e) => setLocalValue(e.target.value)}
              placeholder="Digite sua resposta..."
              className="w-full p-3 rounded-lg border border-input bg-background text-foreground resize-none focus:outline-none focus:ring-2 focus:ring-ring"
              rows={3}
            />
          )}

          {field.field_type === 'number' && (
            <input
              type="number"
              value={localValue}
              onChange={(e) => setLocalValue(e.target.value)}
              placeholder="0"
              className="w-full p-3 rounded-lg border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
          )}

          {field.field_type === 'select' && (
            <select
              value={localValue}
              onChange={(e) => setLocalValue(e.target.value)}
              className="w-full p-3 rounded-lg border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="">Selecione...</option>
              {field.config_json.options?.map((opt) => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
          )}

          {field.field_type === 'date' && (
            <input
              type="date"
              value={localValue}
              onChange={(e) => setLocalValue(e.target.value)}
              className="w-full p-3 rounded-lg border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
          )}

          {(field.field_type === 'photo' || field.field_type === 'evidence') && (
            <div className="border-2 border-dashed border-input rounded-lg p-8 text-center">
              <Camera className="w-12 h-12 mx-auto text-muted-foreground mb-3" />
              <p className="text-sm text-muted-foreground">
                Toque para capturar ou selecionar arquivo
              </p>
            </div>
          )}

          <button
            onClick={handleSave}
            className="w-full mt-6 py-3 px-4 rounded-xl bg-primary text-primary-foreground font-medium touch-target"
          >
            Salvar e Continuar
          </button>
        </div>
      </div>
    </div>
  )
}
