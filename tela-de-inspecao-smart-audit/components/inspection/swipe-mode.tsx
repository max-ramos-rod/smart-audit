'use client'

import { useState, useCallback, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useInspection } from './inspection-context'
import { SwipeCard } from './swipe-card'
import { Check, Minus } from 'lucide-react'

export function SwipeMode() {
  const { 
    answerableFields,
    currentFieldIndex,
    setCurrentFieldIndex,
    setAnswer,
    goToNextField,
    goToPreviousField,
    progress,
    score,
    sections
  } = useInspection()
  
  const [exitDirection, setExitDirection] = useState<'left' | 'right' | null>(null)

  const currentField = answerableFields[currentFieldIndex]

  const handleSwipeComplete = useCallback((direction: 'left' | 'right' | 'na') => {
    if (!currentField) return

    setExitDirection(direction === 'na' ? 'left' : direction)
    
    // Update answer based on swipe direction (only for boolean fields)
    if (currentField.field_type === 'boolean') {
      if (direction === 'right') {
        setAnswer(currentField.key, true)
      } else if (direction === 'left') {
        setAnswer(currentField.key, false)
      } else if (direction === 'na') {
        setAnswer(currentField.key, 'na')
      }
    }

    // Move to next item after animation
    setTimeout(() => {
      setExitDirection(null)
      goToNextField()
    }, 300)
  }, [currentField, setAnswer, goToNextField])

  const pendingCount = progress.total - progress.answered
  const isComplete = pendingCount === 0

  return (
    <div className="flex flex-col h-full">
      {/* Progress Header */}
      <div className="px-4 py-3 bg-card border-b border-border">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-foreground">
            Progresso da Inspeção
          </span>
          <div className="flex items-center gap-2">
            {score !== null && (
              <span className={`text-sm font-semibold ${
                score >= 90 ? 'text-success' : 
                score >= 70 ? 'text-warning' : 'text-destructive'
              }`}>
                Score: {score}%
              </span>
            )}
            <span className="text-sm text-muted-foreground">
              {progress.answered}/{progress.total} ({progress.percentage}%)
            </span>
          </div>
        </div>
        
        {/* Progress Bar */}
        <div className="insp-progress-bar h-2 bg-muted rounded-full overflow-hidden">
          <div className="insp-progress-fill h-full flex">
            <motion.div
              className="bg-success"
              initial={{ width: 0 }}
              animate={{ width: `${(progress.compliant / progress.total) * 100}%` }}
            />
            <motion.div
              className="bg-destructive"
              initial={{ width: 0 }}
              animate={{ width: `${(progress.nonCompliant / progress.total) * 100}%` }}
            />
            <motion.div
              className="bg-warning"
              initial={{ width: 0 }}
              animate={{ width: `${(progress.na / progress.total) * 100}%` }}
            />
          </div>
        </div>
        
        {/* Legend */}
        <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-success" />
            {progress.compliant} Conforme
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-destructive" />
            {progress.nonCompliant} Não Conforme
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-warning" />
            {progress.na} N/A
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-pending" />
            {pendingCount} Pendente
          </span>
        </div>
      </div>

      {/* Section Jump Bar */}
      <div className="section-jump-bar px-4 py-2 bg-muted/50 border-b border-border overflow-x-auto">
        <div className="flex gap-2">
          {sections.map((section, idx) => (
            <button
              key={section.id}
              onClick={() => {
                // Find first field after this section
                const sectionPos = section.position
                const nextSectionPos = sections[idx + 1]?.position ?? Infinity
                const fieldIdx = answerableFields.findIndex(
                  f => f.position > sectionPos && f.position < nextSectionPos
                )
                if (fieldIdx !== -1) setCurrentFieldIndex(fieldIdx)
              }}
              className={`section-jump-chip shrink-0 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                section.progress === 100 
                  ? 'bg-success/20 text-success' 
                  : 'bg-muted text-muted-foreground hover:bg-muted/80'
              }`}
            >
              {section.label.length > 20 ? section.label.slice(0, 20) + '...' : section.label}
              <span className="ml-1 opacity-70">{section.progress}%</span>
            </button>
          ))}
        </div>
      </div>

      {/* Card Area */}
      <div className="flex-1 relative overflow-hidden">
        <AnimatePresence mode="wait">
          {currentField && !isComplete && (
            <motion.div
              key={currentField.id}
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{
                x: exitDirection === 'right' ? 300 : exitDirection === 'left' ? -300 : 0,
                rotate: exitDirection === 'right' ? 15 : exitDirection === 'left' ? -15 : 0,
                opacity: 0,
              }}
              transition={{ duration: 0.3 }}
              className="h-full flex items-center justify-center"
            >
              <SwipeCard
                field={currentField}
                onSwipeComplete={handleSwipeComplete}
                isActive={true}
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* All Done Message */}
        {isComplete && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center p-8">
              <div className="w-20 h-20 rounded-full bg-success/10 flex items-center justify-center mx-auto mb-4">
                <Check className="w-10 h-10 text-success" />
              </div>
              <h3 className="text-xl font-semibold text-foreground mb-2">
                Inspeção Concluída!
              </h3>
              <p className="text-muted-foreground mb-4">
                Todos os campos foram preenchidos.
              </p>
              {score !== null && (
                <div className={`inline-block px-4 py-2 rounded-lg text-lg font-bold ${
                  score >= 90 ? 'bg-success/10 text-success' : 
                  score >= 70 ? 'bg-warning/10 text-warning' : 
                  'bg-destructive/10 text-destructive'
                }`}>
                  Score Final: {score}%
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Quick Navigation */}
      <div className="insp-nav px-4 py-3 bg-card border-t border-border safe-area-bottom">
        <div className="flex items-center justify-between">
          <button
            onClick={goToPreviousField}
            disabled={currentFieldIndex === 0}
            className="px-4 py-2 text-sm font-medium text-foreground disabled:opacity-50 disabled:cursor-not-allowed touch-target"
          >
            ← Anterior
          </button>
          <span className="insp-counter text-sm text-muted-foreground font-mono">
            {currentFieldIndex + 1} / {answerableFields.length}
          </span>
          <button
            onClick={goToNextField}
            disabled={currentFieldIndex >= answerableFields.length - 1}
            className="px-4 py-2 text-sm font-medium text-foreground disabled:opacity-50 disabled:cursor-not-allowed touch-target"
          >
            Próximo →
          </button>
        </div>
      </div>
    </div>
  )
}
