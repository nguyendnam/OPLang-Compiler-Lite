import { useCallback, useEffect, useRef, useState } from 'react'
import { compileSource } from '../../services/compilerApi'
import type { CompilationResult } from '../../types/compiler'

const DEFAULT_OPTIONS = {
  includeAst: true,
  includeJasmin: true
} as const

export function useCompiler() {
  const [result, setResult] = useState<CompilationResult | null>(null)
  const [networkError, setNetworkError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const activeRequest = useRef<AbortController | null>(null)

  useEffect(() => () => activeRequest.current?.abort(), [])

  const compile = useCallback(async (source: string) => {
    activeRequest.current?.abort()
    const controller = new AbortController()
    activeRequest.current = controller
    setLoading(true)
    setNetworkError(null)

    try {
      const nextResult = await compileSource(source, DEFAULT_OPTIONS, controller.signal)
      if (!controller.signal.aborted) setResult(nextResult)
    } catch (error) {
      if (!controller.signal.aborted) {
        setResult(null)
        setNetworkError(
          error instanceof Error ? error.message : 'Compilation request failed.'
        )
      }
    } finally {
      if (activeRequest.current === controller) {
        activeRequest.current = null
        setLoading(false)
      }
    }
  }, [])

  const clearResult = useCallback(() => {
    activeRequest.current?.abort()
    activeRequest.current = null
    setLoading(false)
    setResult(null)
    setNetworkError(null)
  }, [])

  return { result, networkError, loading, compile, clearResult }
}
