/** Loads the catalog (places, variables, questions) once and shares it with every screen. */

import { createContext, useContext, useMemo, type ReactNode } from 'react'
import { api } from './api/endpoints'
import type { Meta, QuestionInfo, VariableInfo } from './api/types'
import { ErrorBox, Skeleton } from './components/ui'
import { useAsync } from './hooks'

interface MetaCtx {
  meta: Meta
  variable: (code: string) => VariableInfo | undefined
  question: (id: string) => QuestionInfo | undefined
}

const Ctx = createContext<MetaCtx | null>(null)

/** Loads the variable, place and region lists once and shares them with every page. */
export function MetaProvider({ children }: { children: ReactNode }) {
  const { data, error } = useAsync(() => api.meta(), [])
  const value = useMemo<MetaCtx | null>(() => {
    if (!data) return null
    const vars = new Map(data.variables.map((v) => [v.code, v]))
    const qs = new Map(data.questions.map((q) => [q.id, q]))
    return { meta: data, variable: (c) => vars.get(c), question: (id) => qs.get(id) }
  }, [data])

  if (error) return <div className="main"><ErrorBox error={error} retry={() => window.location.reload()} /></div>
  if (!value) return <div className="main"><Skeleton height={320} /></div>
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

/** Read the shared metadata (variables, places, regions). */
export function useMeta(): MetaCtx {
  const v = useContext(Ctx)
  if (!v) throw new Error('useMeta must be used inside <MetaProvider>')
  return v
}
