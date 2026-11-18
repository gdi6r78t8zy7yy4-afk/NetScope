import { useEffect, useRef } from 'react'
import cytoscape from 'cytoscape'

interface TopologyViewProps {
  nodes: any[]
  edges: any[]
}

export function TopologyView({ nodes, edges }: TopologyViewProps) {
  const cyRef = useRef<HTMLDivElement>(null)
  let cy: cytoscape.Core | null = null

  useEffect(() => {
    if (!cyRef.current) return

    cy = cytoscape({
      container: cyRef.current,
      elements: [...nodes, ...edges],
      style: [
        {
          selector: 'node',
          style: {
            label: 'data(label)',
            'background-color': '#10b981',
            'border-width': 2,
            'border-color': '#fff'
          }
        },
        {
          selector: 'edge',
          style: {
            width: 1,
            'line-color': '#475569',
            'arrow-scale': 1.2
          }
        }
      ],
      layout: {
        name: 'cose',
        animate: true
      },
      zoomingEnabled: true,
      userZoomingEnabled: true
    })

    return () => {
      if (cy) {
        cy.destroy()
      }
    }
  }, [nodes, edges])

  return (
    <div ref={cyRef} style={{ height: '100%', width: '100%' }} />
  )
}

export default TopologyView
