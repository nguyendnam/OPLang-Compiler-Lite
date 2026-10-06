import { useCallback, useEffect, useState } from 'react'
import { CodeEditor } from './components/CodeEditor'
import { Header } from './components/Header'
import { ResultPanel } from './components/ResultPanel'
import { compilerExamples, type CompilerExample } from './data/examples'
import { useCompiler } from './features/compiler/useCompiler'
import './styles.css'

const SOURCE_STORAGE_KEY = 'oplang-compiler-lite:source'
const DEFAULT_SOURCE = compilerExamples[0].source

export default function App() {
  const [source, setSource] = useState(
    () => {
      try {
        return localStorage.getItem(SOURCE_STORAGE_KEY) ?? DEFAULT_SOURCE
      } catch {
        return DEFAULT_SOURCE
      }
    }
  )
  const { result, networkError, loading, compile, clearResult } = useCompiler()

  useEffect(() => {
    try {
      localStorage.setItem(SOURCE_STORAGE_KEY, source)
    } catch {
      // Editing still works when browser storage is unavailable or full.
    }
  }, [source])

  const onCompile = useCallback(() => {
    if (!loading) void compile(source)
  }, [compile, loading, source])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (!(event.ctrlKey || event.metaKey) || event.key !== 'Enter') return
      event.preventDefault()
      onCompile()
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onCompile])

  const updateSource = useCallback(
    (nextSource: string) => {
      setSource(nextSource)
      clearResult()
    },
    [clearResult]
  )

  const selectExample = useCallback(
    (example: CompilerExample) => updateSource(example.source),
    [updateSource]
  )

  return (
    <main>
      <Header
        examples={compilerExamples}
        loading={loading}
        onCompile={onCompile}
        onSelectExample={selectExample}
      />

      <section className="workspace">
        <div className="column">
          <div className="sectionTitle">Source Code</div>
          <CodeEditor value={source} onChange={updateSource} />
        </div>
        <div className="column">
          <div className="sectionTitle">Result</div>
          <ResultPanel result={result} networkError={networkError} loading={loading} />
        </div>
      </section>
    </main>
  )
}
