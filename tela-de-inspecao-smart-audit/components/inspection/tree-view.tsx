'use client'

import { useState, useMemo, useRef, useCallback } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  ChevronRight, 
  ChevronDown, 
  Check, 
  X, 
  Minus,
  Paperclip,
  Camera,
  Mic,
  Video,
  FileText,
  Search
} from 'lucide-react'
import { useInspection } from './inspection-context'
import type { InspectionItem, InspectionGroup, InspectionSubgroup, FlatItem } from '@/lib/types'
import { cn } from '@/lib/utils'

export function TreeView() {
  const { 
    inspection, 
    setItemStatus, 
    getEvidenceCount, 
    getGroupProgress,
    addEvidence,
    setCurrentItem,
    currentItemId 
  } = useInspection()
  
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set())
  const [expandedSubgroups, setExpandedSubgroups] = useState<Set<string>>(new Set())
  const [selectedItem, setSelectedItem] = useState<InspectionItem | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  
  const parentRef = useRef<HTMLDivElement>(null)

  // Flatten tree structure for virtualization
  const flatItems = useMemo((): FlatItem[] => {
    const items: FlatItem[] = []
    
    for (const group of inspection.groups) {
      // Add group header
      items.push({
        type: 'group',
        id: group.id,
        data: group,
        depth: 0,
      })

      if (expandedGroups.has(group.id)) {
        // Add subgroups and their items
        for (const subgroup of group.subgroups) {
          items.push({
            type: 'subgroup',
            id: subgroup.id,
            data: subgroup,
            depth: 1,
            groupId: group.id,
          })

          if (expandedSubgroups.has(subgroup.id)) {
            for (const item of subgroup.items) {
              // Filter by search
              if (searchQuery && !item.title.toLowerCase().includes(searchQuery.toLowerCase()) &&
                  !item.code.toLowerCase().includes(searchQuery.toLowerCase())) {
                continue
              }
              items.push({
                type: 'item',
                id: item.id,
                data: item,
                depth: 2,
                groupId: group.id,
                subgroupId: subgroup.id,
              })
            }
          }
        }

        // Add direct items (no subgroup)
        for (const item of group.items) {
          if (searchQuery && !item.title.toLowerCase().includes(searchQuery.toLowerCase()) &&
              !item.code.toLowerCase().includes(searchQuery.toLowerCase())) {
            continue
          }
          items.push({
            type: 'item',
            id: item.id,
            data: item,
            depth: 1,
            groupId: group.id,
          })
        }
      }
    }

    return items
  }, [inspection, expandedGroups, expandedSubgroups, searchQuery])

  const virtualizer = useVirtualizer({
    count: flatItems.length,
    getScrollElement: () => parentRef.current,
    estimateSize: useCallback((index: number) => {
      const item = flatItems[index]
      if (item.type === 'group') return 56
      if (item.type === 'subgroup') return 48
      return 72
    }, [flatItems]),
    overscan: 10,
  })

  const toggleGroup = (groupId: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev)
      if (next.has(groupId)) {
        next.delete(groupId)
      } else {
        next.add(groupId)
      }
      return next
    })
  }

  const toggleSubgroup = (subgroupId: string) => {
    setExpandedSubgroups(prev => {
      const next = new Set(prev)
      if (next.has(subgroupId)) {
        next.delete(subgroupId)
      } else {
        next.add(subgroupId)
      }
      return next
    })
  }

  const handleItemTap = (item: InspectionItem) => {
    setSelectedItem(item)
    setCurrentItem(item.id)
  }

  const handleQuickAction = (item: InspectionItem, status: 'compliant' | 'non-compliant') => {
    setItemStatus(item.id, status)
  }

  const renderGroupRow = (group: InspectionGroup) => {
    const isExpanded = expandedGroups.has(group.id)
    const progress = getGroupProgress(group.id)
    const progressPercent = progress.total > 0 ? Math.round((progress.completed / progress.total) * 100) : 0

    return (
      <button
        onClick={() => toggleGroup(group.id)}
        className="w-full flex items-center gap-3 px-4 py-3 bg-card hover:bg-muted/50 transition-colors touch-target"
      >
        <div className={cn(
          "w-8 h-8 rounded-lg flex items-center justify-center transition-colors",
          progressPercent === 100 ? "bg-success/10" : "bg-primary/10"
        )}>
          {isExpanded ? (
            <ChevronDown className="w-5 h-5 text-primary" />
          ) : (
            <ChevronRight className="w-5 h-5 text-primary" />
          )}
        </div>
        <div className="flex-1 text-left">
          <h3 className="font-medium text-foreground">{group.name}</h3>
          <div className="flex items-center gap-2 mt-1">
            <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden max-w-32">
              <div 
                className="h-full bg-success transition-all"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <span className="text-xs text-muted-foreground">
              {progress.completed}/{progress.total}
            </span>
          </div>
        </div>
      </button>
    )
  }

  const renderSubgroupRow = (subgroup: InspectionSubgroup) => {
    const isExpanded = expandedSubgroups.has(subgroup.id)
    const completed = subgroup.items.filter(i => i.status !== 'pending').length

    return (
      <button
        onClick={() => toggleSubgroup(subgroup.id)}
        className="w-full flex items-center gap-3 px-4 py-2.5 pl-12 bg-card hover:bg-muted/50 transition-colors touch-target"
      >
        {isExpanded ? (
          <ChevronDown className="w-4 h-4 text-muted-foreground" />
        ) : (
          <ChevronRight className="w-4 h-4 text-muted-foreground" />
        )}
        <span className="flex-1 text-left text-sm font-medium text-foreground">
          {subgroup.name}
        </span>
        <span className="text-xs text-muted-foreground">
          {completed}/{subgroup.items.length}
        </span>
      </button>
    )
  }

  const renderItemRow = (item: InspectionItem, depth: number) => {
    const evidenceCount = getEvidenceCount(item.id)

    return (
      <div 
        className={cn(
          "flex items-center gap-3 px-4 py-3 bg-card border-b border-border/50",
          depth === 2 && "pl-16",
          depth === 1 && "pl-12"
        )}
      >
        {/* Status Indicator */}
        <div className={cn(
          "w-8 h-8 rounded-full flex items-center justify-center shrink-0",
          item.status === 'pending' && "bg-pending/20",
          item.status === 'compliant' && "bg-success/20",
          item.status === 'non-compliant' && "bg-destructive/20"
        )}>
          {item.status === 'pending' && <Minus className="w-4 h-4 text-pending-foreground" />}
          {item.status === 'compliant' && <Check className="w-4 h-4 text-success" />}
          {item.status === 'non-compliant' && <X className="w-4 h-4 text-destructive" />}
        </div>

        {/* Content */}
        <button 
          onClick={() => handleItemTap(item)}
          className="flex-1 text-left min-w-0"
        >
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-muted-foreground">{item.code}</span>
            {evidenceCount > 0 && (
              <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-primary/10 text-primary text-xs rounded-full">
                <Paperclip className="w-3 h-3" />
                {evidenceCount}
              </span>
            )}
          </div>
          <p className="text-sm text-foreground truncate mt-0.5">{item.title}</p>
        </button>

        {/* Quick Actions */}
        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={() => handleQuickAction(item, 'compliant')}
            className={cn(
              "w-10 h-10 rounded-full flex items-center justify-center transition-colors touch-target",
              item.status === 'compliant' 
                ? "bg-success text-success-foreground" 
                : "bg-muted hover:bg-success/20 text-muted-foreground hover:text-success"
            )}
          >
            <Check className="w-5 h-5" />
          </button>
          <button
            onClick={() => handleQuickAction(item, 'non-compliant')}
            className={cn(
              "w-10 h-10 rounded-full flex items-center justify-center transition-colors touch-target",
              item.status === 'non-compliant' 
                ? "bg-destructive text-destructive-foreground" 
                : "bg-muted hover:bg-destructive/20 text-muted-foreground hover:text-destructive"
            )}
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Search Bar */}
      <div className="px-4 py-3 bg-card border-b border-border">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Buscar por código ou título..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-muted rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
      </div>

      {/* Virtualized List */}
      <div 
        ref={parentRef}
        className="flex-1 overflow-auto"
      >
        <div
          style={{
            height: `${virtualizer.getTotalSize()}px`,
            width: '100%',
            position: 'relative',
          }}
        >
          {virtualizer.getVirtualItems().map(virtualRow => {
            const flatItem = flatItems[virtualRow.index]
            
            return (
              <div
                key={flatItem.id}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: `${virtualRow.size}px`,
                  transform: `translateY(${virtualRow.start}px)`,
                }}
              >
                {flatItem.type === 'group' && renderGroupRow(flatItem.data as InspectionGroup)}
                {flatItem.type === 'subgroup' && renderSubgroupRow(flatItem.data as InspectionSubgroup)}
                {flatItem.type === 'item' && renderItemRow(flatItem.data as InspectionItem, flatItem.depth)}
              </div>
            )
          })}
        </div>
      </div>

      {/* Item Detail Modal */}
      <AnimatePresence>
        {selectedItem && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-foreground/50 flex items-end justify-center"
            onClick={() => setSelectedItem(null)}
          >
            <motion.div
              initial={{ y: '100%' }}
              animate={{ y: 0 }}
              exit={{ y: '100%' }}
              className="w-full max-w-lg bg-card rounded-t-2xl max-h-[80vh] overflow-auto safe-area-bottom"
              onClick={e => e.stopPropagation()}
            >
              <div className="sticky top-0 bg-card px-6 pt-4 pb-2 border-b border-border">
                <div className="w-12 h-1 bg-muted rounded-full mx-auto mb-4" />
                <div className="flex items-center justify-between">
                  <span className="text-sm font-mono text-muted-foreground">{selectedItem.code}</span>
                  <span className={cn(
                    "px-2 py-1 text-xs font-medium rounded-full",
                    selectedItem.status === 'pending' && "bg-pending text-pending-foreground",
                    selectedItem.status === 'compliant' && "bg-success text-success-foreground",
                    selectedItem.status === 'non-compliant' && "bg-destructive text-destructive-foreground"
                  )}>
                    {selectedItem.status === 'pending' && 'Pendente'}
                    {selectedItem.status === 'compliant' && 'Conforme'}
                    {selectedItem.status === 'non-compliant' && 'Não Conforme'}
                  </span>
                </div>
              </div>
              
              <div className="p-6">
                <h3 className="text-lg font-semibold text-foreground mb-2">
                  {selectedItem.title}
                </h3>
                {selectedItem.description && (
                  <p className="text-sm text-muted-foreground mb-4">
                    {selectedItem.description}
                  </p>
                )}
                {selectedItem.helpText && (
                  <div className="p-3 bg-muted rounded-lg mb-6">
                    <p className="text-sm text-muted-foreground">
                      <strong className="text-foreground">Orientação:</strong> {selectedItem.helpText}
                    </p>
                  </div>
                )}

                {/* Evidence Section */}
                <div className="mb-6">
                  <h4 className="text-sm font-medium text-foreground mb-3">Anexar Evidência</h4>
                  <div className="grid grid-cols-4 gap-3">
                    <button
                      onClick={() => addEvidence(selectedItem.id, 'photo')}
                      className="flex flex-col items-center gap-2 p-3 rounded-xl bg-muted hover:bg-muted/80 transition-colors"
                    >
                      <Camera className="w-5 h-5 text-primary" />
                      <span className="text-xs font-medium">Foto</span>
                    </button>
                    <button
                      onClick={() => addEvidence(selectedItem.id, 'video')}
                      className="flex flex-col items-center gap-2 p-3 rounded-xl bg-muted hover:bg-muted/80 transition-colors"
                    >
                      <Video className="w-5 h-5 text-primary" />
                      <span className="text-xs font-medium">Vídeo</span>
                    </button>
                    <button
                      onClick={() => addEvidence(selectedItem.id, 'audio')}
                      className="flex flex-col items-center gap-2 p-3 rounded-xl bg-muted hover:bg-muted/80 transition-colors"
                    >
                      <Mic className="w-5 h-5 text-primary" />
                      <span className="text-xs font-medium">Áudio</span>
                    </button>
                    <button
                      onClick={() => addEvidence(selectedItem.id, 'note', 'Nova nota')}
                      className="flex flex-col items-center gap-2 p-3 rounded-xl bg-muted hover:bg-muted/80 transition-colors"
                    >
                      <FileText className="w-5 h-5 text-primary" />
                      <span className="text-xs font-medium">Nota</span>
                    </button>
                  </div>
                </div>

                {/* Status Actions */}
                <div className="flex gap-3">
                  <button
                    onClick={() => {
                      setItemStatus(selectedItem.id, 'compliant')
                      setSelectedItem(null)
                    }}
                    className={cn(
                      "flex-1 py-3 px-4 rounded-xl font-medium transition-colors touch-target",
                      selectedItem.status === 'compliant'
                        ? "bg-success text-success-foreground"
                        : "bg-muted hover:bg-success/20 text-foreground"
                    )}
                  >
                    <Check className="w-5 h-5 inline-block mr-2" />
                    Conforme
                  </button>
                  <button
                    onClick={() => {
                      setItemStatus(selectedItem.id, 'non-compliant')
                      setSelectedItem(null)
                    }}
                    className={cn(
                      "flex-1 py-3 px-4 rounded-xl font-medium transition-colors touch-target",
                      selectedItem.status === 'non-compliant'
                        ? "bg-destructive text-destructive-foreground"
                        : "bg-muted hover:bg-destructive/20 text-foreground"
                    )}
                  >
                    <X className="w-5 h-5 inline-block mr-2" />
                    Não Conforme
                  </button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
