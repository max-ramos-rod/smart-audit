'use client'

import { createContext, useContext, useState, useCallback, useMemo, type ReactNode } from 'react'
import type { 
  FormField, 
  FormVersion, 
  DraftAnswers, 
  FieldValue,
  Attachment,
  InspectionProgress,
  EvidenceMetadata
} from '@/lib/types'
import { 
  getVisibleFields, 
  calculateProgress, 
  calculateWeightedScore,
  getFieldStatus,
  mockFormVersion,
  mockDraftAnswers,
  mockAttachments
} from '@/lib/mock-data'

type ViewMode = 'swipe' | 'list'

interface InspectionContextType {
  // Form data
  formVersion: FormVersion | null
  setFormVersion: (version: FormVersion) => void
  
  // Answers (draft)
  answers: DraftAnswers
  setAnswer: (fieldKey: string, value: FieldValue) => void
  
  // Attachments
  attachments: Map<string, Attachment[]>
  addAttachment: (fieldKey: string, attachment: Attachment) => void
  removeAttachment: (fieldKey: string, attachmentId: string) => void
  
  // Pending evidences (before upload)
  pendingEvidences: Map<string, EvidenceMetadata[]>
  addPendingEvidence: (fieldKey: string, evidence: EvidenceMetadata) => void
  removePendingEvidence: (fieldKey: string, evidenceId: string) => void
  
  // Computed values
  visibleFields: FormField[]
  answerableFields: FormField[]
  progress: InspectionProgress
  score: number | null
  
  // Navigation
  currentFieldIndex: number
  setCurrentFieldIndex: (index: number) => void
  goToNextField: () => void
  goToPreviousField: () => void
  goToField: (fieldId: string) => void
  
  // View mode
  viewMode: ViewMode
  setViewMode: (mode: ViewMode) => void
  
  // Search
  searchQuery: string
  setSearchQuery: (query: string) => void
  
  // Sections for quick navigation
  sections: { id: string; label: string; position: number; progress: number }[]
  
  // Field status helper
  getFieldStatus: (field: FormField) => 'pending' | 'compliant' | 'non_compliant' | 'na'
}

const InspectionContext = createContext<InspectionContextType | null>(null)

export function useInspection() {
  const context = useContext(InspectionContext)
  if (!context) {
    throw new Error('useInspection must be used within InspectionProvider')
  }
  return context
}

interface InspectionProviderProps {
  children: ReactNode
  initialFormVersion?: FormVersion
  initialAnswers?: DraftAnswers
  initialAttachments?: Attachment[]
}

export function InspectionProvider({
  children,
  initialFormVersion = mockFormVersion,
  initialAnswers = mockDraftAnswers,
  initialAttachments = mockAttachments,
}: InspectionProviderProps) {
  const [formVersion, setFormVersion] = useState<FormVersion | null>(initialFormVersion)
  const [answers, setAnswers] = useState<DraftAnswers>(initialAnswers)
  const [attachments, setAttachments] = useState<Map<string, Attachment[]>>(() => {
    const map = new Map<string, Attachment[]>()
    for (const att of initialAttachments) {
      const existing = map.get(att.field_key) || []
      map.set(att.field_key, [...existing, att])
    }
    return map
  })
  const [pendingEvidences, setPendingEvidences] = useState<Map<string, EvidenceMetadata[]>>(new Map())
  const [currentFieldIndex, setCurrentFieldIndex] = useState(0)
  const [viewMode, setViewMode] = useState<ViewMode>('swipe')
  const [searchQuery, setSearchQuery] = useState('')

  const fields = formVersion?.fields ?? []

  // Campos visíveis (respeitando visible_if)
  const visibleFields = useMemo(() => {
    return getVisibleFields(fields, answers)
  }, [fields, answers])

  // Campos respondíveis (excluindo sections)
  const answerableFields = useMemo(() => {
    return visibleFields.filter(f => f.field_type !== 'section')
  }, [visibleFields])

  // Progresso
  const progress = useMemo(() => {
    return calculateProgress(fields, answers)
  }, [fields, answers])

  // Score ponderado
  const score = useMemo(() => {
    return calculateWeightedScore(fields, answers)
  }, [fields, answers])

  // Seções com progresso
  const sections = useMemo(() => {
    const sectionFields = fields.filter(f => f.field_type === 'section')
    
    return sectionFields.map((section, idx) => {
      const nextSectionPos = sectionFields[idx + 1]?.position ?? Infinity
      const sectionItems = answerableFields.filter(
        f => f.position > section.position && f.position < nextSectionPos
      )
      
      const answeredCount = sectionItems.filter(f => {
        const value = answers[f.key]
        return value !== undefined && value !== null
      }).length
      
      return {
        id: section.id,
        label: section.label,
        position: section.position,
        progress: sectionItems.length > 0 
          ? Math.round((answeredCount / sectionItems.length) * 100)
          : 100,
      }
    })
  }, [fields, answerableFields, answers])

  // Actions
  const setAnswer = useCallback((fieldKey: string, value: FieldValue) => {
    setAnswers(prev => ({ ...prev, [fieldKey]: value }))
  }, [])

  const addAttachment = useCallback((fieldKey: string, attachment: Attachment) => {
    setAttachments(prev => {
      const next = new Map(prev)
      const existing = next.get(fieldKey) || []
      next.set(fieldKey, [...existing, attachment])
      return next
    })
  }, [])

  const removeAttachment = useCallback((fieldKey: string, attachmentId: string) => {
    setAttachments(prev => {
      const next = new Map(prev)
      const existing = next.get(fieldKey) || []
      next.set(fieldKey, existing.filter(a => a.id !== attachmentId))
      return next
    })
  }, [])

  const addPendingEvidence = useCallback((fieldKey: string, evidence: EvidenceMetadata) => {
    setPendingEvidences(prev => {
      const next = new Map(prev)
      const existing = next.get(fieldKey) || []
      next.set(fieldKey, [...existing, evidence])
      return next
    })
  }, [])

  const removePendingEvidence = useCallback((fieldKey: string, evidenceId: string) => {
    setPendingEvidences(prev => {
      const next = new Map(prev)
      const existing = next.get(fieldKey) || []
      next.set(fieldKey, existing.filter(e => e.id !== evidenceId))
      return next
    })
  }, [])

  const goToNextField = useCallback(() => {
    setCurrentFieldIndex(prev => Math.min(prev + 1, answerableFields.length - 1))
  }, [answerableFields.length])

  const goToPreviousField = useCallback(() => {
    setCurrentFieldIndex(prev => Math.max(prev - 1, 0))
  }, [])

  const goToField = useCallback((fieldId: string) => {
    const index = answerableFields.findIndex(f => f.id === fieldId)
    if (index !== -1) {
      setCurrentFieldIndex(index)
    }
  }, [answerableFields])

  const getFieldStatusFn = useCallback((field: FormField) => {
    return getFieldStatus(field, answers)
  }, [answers])

  const value: InspectionContextType = {
    formVersion,
    setFormVersion,
    answers,
    setAnswer,
    attachments,
    addAttachment,
    removeAttachment,
    pendingEvidences,
    addPendingEvidence,
    removePendingEvidence,
    visibleFields,
    answerableFields,
    progress,
    score,
    currentFieldIndex,
    setCurrentFieldIndex,
    goToNextField,
    goToPreviousField,
    goToField,
    viewMode,
    setViewMode,
    searchQuery,
    setSearchQuery,
    sections,
    getFieldStatus: getFieldStatusFn,
  }

  return (
    <InspectionContext.Provider value={value}>
      {children}
    </InspectionContext.Provider>
  )
}
