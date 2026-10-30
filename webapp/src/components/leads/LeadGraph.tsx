import { useEffect, useMemo, useRef } from 'react'
import ForceGraph2D, { type ForceGraphMethods } from 'react-force-graph-2d'
import { leadSubgraph } from '../../mock'
import type { GraphLink, GraphNode, Lead } from '../../types'

const kindColor: Record<GraphNode['kind'], string> = {
  Founder: '#0c0f14',
  Company: '#4a5160',
  Person: '#2f5bd3',
  Signal: '#868e9c',
  School: '#7c3aed',
  Investor: '#0e7c66',
}

type N = GraphNode & { x?: number; y?: number; fx?: number; fy?: number }
type L = Omit<GraphLink, 'source' | 'target'> & { source: string | N; target: string | N }

export function LeadGraph({ lead, width }: { lead: Lead; width: number }) {
  // Subgraphs are tiny, so pin them left to right: You → shared node → person → company → signals.
  const data = useMemo(() => {
    const g = leadSubgraph(lead)
    const signals = g.nodes.filter((n) => n.kind === 'Signal')
    const at: Record<string, [number, number]> = { founder: [-170, 0], via: [-85, -60], person: [0, 0] }
    const nodes: N[] = g.nodes.map((n) => {
      const [x, y] =
        at[n.id] ?? (n.kind === 'Signal' ? [180, (signals.indexOf(n) - (signals.length - 1) / 2) * 50] : [90, 0])
      return { ...n, x, y, fx: x, fy: y }
    })
    return { nodes, links: g.links as L[] }
  }, [lead])
  const ref = useRef<ForceGraphMethods<N, L> | undefined>(undefined)

  useEffect(() => {
    const t = setTimeout(() => ref.current?.zoomToFit(0, 48), 60)
    return () => clearTimeout(t)
  }, [data])

  return (
    <div className="overflow-hidden rounded-xl border border-line bg-surface">
      <ForceGraph2D<N, L>
        ref={ref}
        graphData={data}
        width={width}
        height={260}
        backgroundColor="#ffffff"
        cooldownTicks={1}
        enableZoomInteraction={false}
        enablePanInteraction={false}
        enableNodeDrag={false}
        linkColor={(l) => (l.warm ? '#9bd20f' : '#c7ccd5')}
        linkWidth={(l) => (l.warm ? 3.5 : 1)}
        linkLineDash={(l) => (l.rel === 'HAS_SIGNAL' ? [3, 3] : null)}
        nodeCanvasObject={(node, ctx, scale) => {
          const r = node.kind === 'Signal' ? 4 : node.kind === 'Founder' || node.kind === 'Company' ? 8 : 6
          ctx.beginPath()
          ctx.arc(node.x!, node.y!, r, 0, 2 * Math.PI)
          ctx.fillStyle = kindColor[node.kind]
          ctx.fill()
          const fs = Math.max(11 / scale, 3)
          ctx.font = `${node.kind === 'Signal' ? 400 : 500} ${fs}px Geist, sans-serif`
          ctx.textAlign = 'center'
          ctx.textBaseline = 'top'
          ctx.fillStyle = node.kind === 'Signal' ? '#868e9c' : '#0c0f14'
          ctx.fillText(node.label, node.x!, node.y! + r + 3)
        }}
        nodePointerAreaPaint={(node, color, ctx) => {
          ctx.fillStyle = color
          ctx.beginPath()
          ctx.arc(node.x!, node.y!, 10, 0, 2 * Math.PI)
          ctx.fill()
        }}
        nodeLabel={(n) => n.kind}
      />
      <div className="flex flex-wrap gap-x-4 gap-y-1 border-t border-line px-4 py-2 text-[11px] text-ink-3">
        {(['Founder', 'Person', 'Company', 'School', 'Investor', 'Signal'] as const).map((k) => (
          <span key={k} className="flex items-center gap-1.5">
            <span className="size-2 rounded-full" style={{ background: kindColor[k] }} />
            {k === 'Founder' ? 'You' : k}
          </span>
        ))}
        <span className="ml-auto flex items-center gap-1.5">
          <span className="h-0.5 w-4 rounded bg-accent" /> shared connection
        </span>
      </div>
    </div>
  )
}
