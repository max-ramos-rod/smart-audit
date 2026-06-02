'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Menu, 
  X, 
  LayoutList, 
  Layers, 
  Settings,
  Download,
  Upload,
  BarChart3,
  Clock
} from 'lucide-react'
import { useInspection } from './inspection-context'
import { SwipeMode } from './swipe-mode'
import { TreeView } from './tree-view'
import { cn } from '@/lib/utils'

export function InspectionForm() {
  const { inspection, viewMode, setViewMode, getProgress } = useInspection()
  const [showSidebar, setShowSidebar] = useState(false)
  
  const progress = getProgress()
  const progressPercent = Math.round((progress.completed / progress.total) * 100)

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Header */}
      <header className="shrink-0 px-4 py-3 bg-sidebar text-sidebar-foreground safe-area-top">
        <div className="flex items-center justify-between">
          <button 
            onClick={() => setShowSidebar(true)}
            className="w-10 h-10 flex items-center justify-center rounded-lg hover:bg-sidebar-accent transition-colors touch-target"
          >
            <Menu className="w-5 h-5" />
          </button>
          
          <div className="text-center">
            <h1 className="text-sm font-semibold truncate max-w-48">
              {inspection.title}
            </h1>
            <p className="text-xs text-sidebar-foreground/70">
              {progressPercent}% concluído
            </p>
          </div>

          {/* View Mode Toggle */}
          <div className="flex items-center bg-sidebar-accent rounded-lg p-1">
            <button
              onClick={() => setViewMode('swipe')}
              className={cn(
                "w-9 h-9 flex items-center justify-center rounded-md transition-colors touch-target",
                viewMode === 'swipe' 
                  ? "bg-sidebar-primary text-sidebar-primary-foreground" 
                  : "text-sidebar-foreground/70 hover:text-sidebar-foreground"
              )}
              title="Modo Cartões"
            >
              <Layers className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('tree')}
              className={cn(
                "w-9 h-9 flex items-center justify-center rounded-md transition-colors touch-target",
                viewMode === 'tree' 
                  ? "bg-sidebar-primary text-sidebar-primary-foreground" 
                  : "text-sidebar-foreground/70 hover:text-sidebar-foreground"
              )}
              title="Modo Lista"
            >
              <LayoutList className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden">
        <AnimatePresence mode="wait">
          {viewMode === 'swipe' ? (
            <motion.div
              key="swipe"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="h-full"
            >
              <SwipeMode />
            </motion.div>
          ) : (
            <motion.div
              key="tree"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="h-full"
            >
              <TreeView />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Sidebar */}
      <AnimatePresence>
        {showSidebar && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-foreground/50"
              onClick={() => setShowSidebar(false)}
            />
            <motion.aside
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              className="fixed left-0 top-0 bottom-0 z-50 w-80 max-w-[85vw] bg-sidebar text-sidebar-foreground flex flex-col safe-area-top"
            >
              {/* Sidebar Header */}
              <div className="flex items-center justify-between px-4 py-4 border-b border-sidebar-border">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-sidebar-primary flex items-center justify-center">
                    <BarChart3 className="w-5 h-5 text-sidebar-primary-foreground" />
                  </div>
                  <div>
                    <h2 className="font-semibold">Smart Audit</h2>
                    <p className="text-xs text-sidebar-foreground/70">v1.0.0</p>
                  </div>
                </div>
                <button 
                  onClick={() => setShowSidebar(false)}
                  className="w-10 h-10 flex items-center justify-center rounded-lg hover:bg-sidebar-accent transition-colors touch-target"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Inspection Info */}
              <div className="p-4 border-b border-sidebar-border">
                <h3 className="font-medium mb-1">{inspection.title}</h3>
                {inspection.description && (
                  <p className="text-sm text-sidebar-foreground/70 mb-3">
                    {inspection.description}
                  </p>
                )}
                
                {/* Progress Stats */}
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="p-2 rounded-lg bg-success/10">
                    <p className="text-lg font-semibold text-success">{progress.compliant}</p>
                    <p className="text-xs text-sidebar-foreground/70">Conforme</p>
                  </div>
                  <div className="p-2 rounded-lg bg-destructive/10">
                    <p className="text-lg font-semibold text-destructive">{progress.nonCompliant}</p>
                    <p className="text-xs text-sidebar-foreground/70">Não Conforme</p>
                  </div>
                  <div className="p-2 rounded-lg bg-pending/10">
                    <p className="text-lg font-semibold text-pending-foreground">{progress.total - progress.completed}</p>
                    <p className="text-xs text-sidebar-foreground/70">Pendente</p>
                  </div>
                </div>
              </div>

              {/* Groups Overview */}
              <div className="flex-1 overflow-auto p-4">
                <h4 className="text-xs font-medium text-sidebar-foreground/70 uppercase tracking-wide mb-3">
                  Grupos de Inspeção
                </h4>
                <div className="space-y-2">
                  {inspection.groups.map(group => {
                    let total = group.items.length
                    let completed = group.items.filter(i => i.status !== 'pending').length
                    
                    for (const subgroup of group.subgroups) {
                      total += subgroup.items.length
                      completed += subgroup.items.filter(i => i.status !== 'pending').length
                    }
                    
                    const percent = total > 0 ? Math.round((completed / total) * 100) : 0

                    return (
                      <div 
                        key={group.id}
                        className="p-3 rounded-lg bg-sidebar-accent"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium truncate pr-2">
                            {group.name}
                          </span>
                          <span className="text-xs text-sidebar-foreground/70 shrink-0">
                            {completed}/{total}
                          </span>
                        </div>
                        <div className="h-1.5 bg-sidebar-border rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-sidebar-primary transition-all"
                            style={{ width: `${percent}%` }}
                          />
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* Sidebar Footer */}
              <div className="p-4 border-t border-sidebar-border space-y-2 safe-area-bottom">
                <button className="w-full flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-sidebar-accent transition-colors touch-target">
                  <Download className="w-5 h-5 text-sidebar-foreground/70" />
                  <span className="text-sm font-medium">Exportar Relatório</span>
                </button>
                <button className="w-full flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-sidebar-accent transition-colors touch-target">
                  <Upload className="w-5 h-5 text-sidebar-foreground/70" />
                  <span className="text-sm font-medium">Sincronizar</span>
                </button>
                <button className="w-full flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-sidebar-accent transition-colors touch-target">
                  <Settings className="w-5 h-5 text-sidebar-foreground/70" />
                  <span className="text-sm font-medium">Configurações</span>
                </button>
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}
