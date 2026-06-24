/**
 * Decorative, abstract "narrative network over Europe" motif for the landing hero.
 * Purely ornamental (the hero marks it aria-hidden), so it carries no semantic role.
 * Nodes loosely evoke the ten covered countries; edges suggest narratives spreading
 * across borders. Drawn with currentColor so callers control the tint via text-*.
 */
export function EuropeMotif({ className }: { className?: string }) {
  // Loosely geographic node layout (viewBox 0..200). Not to scale — evocative only.
  const nodes: [number, number][] = [
    [70, 120], // Spain / Portugal cluster
    [60, 110],
    [95, 95], // France
    [120, 70], // Germany
    [115, 110], // Italy
    [150, 60], // Poland
    [100, 60], // Netherlands
    [125, 35], // Sweden
    [140, 80], // Hungary
    [150, 115], // Greece
  ];

  const edges: [number, number][] = [
    [0, 1],
    [1, 2],
    [2, 3],
    [2, 6],
    [3, 6],
    [3, 7],
    [3, 5],
    [5, 8],
    [3, 8],
    [4, 8],
    [2, 4],
    [4, 9],
    [8, 9],
    [3, 4],
  ];

  return (
    <svg
      className={className}
      viewBox="0 0 200 160"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      focusable="false"
    >
      <g stroke="currentColor" strokeWidth="0.6" opacity="0.8">
        {edges.map(([a, b], i) => (
          <line
            key={i}
            x1={nodes[a][0]}
            y1={nodes[a][1]}
            x2={nodes[b][0]}
            y2={nodes[b][1]}
          />
        ))}
      </g>
      <g fill="currentColor">
        {nodes.map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r={i % 3 === 0 ? 3.2 : 2.2} />
        ))}
      </g>
    </svg>
  );
}
