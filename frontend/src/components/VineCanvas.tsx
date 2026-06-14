import React, { useEffect, useRef } from 'react'

interface VineCanvasProps {
  leafCount: number
  color?: string
}

const VineCanvas: React.FC<VineCanvasProps> = ({ leafCount, color = '#22c55e' }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationRef = useRef<number>()

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    
    // Set canvas size
    const resize = () => {
      canvas.width = canvas.offsetWidth * 2
      canvas.height = canvas.offsetHeight * 2
      ctx.scale(2, 2)
    }
    resize()
    window.addEventListener('resize', resize)
    
    // Animation variables
    let time = 0
    const leaves: {x: number, y: number, size: number, angle: number, sway: number}[] = []
    
    // Generate leaves based on leafCount
    for (let i = 0; i < leafCount; i++) {
      leaves.push({
        x: Math.random() * canvas.offsetWidth,
        y: Math.random() * canvas.offsetHeight,
        size: 8 + Math.random() * 12,
        angle: Math.random() * Math.PI * 2,
        sway: Math.random() * 0.02 + 0.01
      })
    }
    
    // Draw vine
    const drawVine = () => {
      const width = canvas.offsetWidth
      const height = canvas.offsetHeight
      
      ctx.clearRect(0, 0, width, height)
      
      // Draw main vine path
      ctx.beginPath()
      ctx.strokeStyle = color
      ctx.lineWidth = 3
      ctx.lineCap = 'round'
      
      for (let x = 0; x < width; x += 5) {
        const y = height / 2 + Math.sin(x * 0.01 + time) * 30 + Math.sin(x * 0.03) * 15
        if (x === 0) {
          ctx.moveTo(x, y)
        } else {
          ctx.lineTo(x, y)
        }
      }
      ctx.stroke()
      
      // Draw branches
      for (let i = 0; i < 5; i++) {
        ctx.beginPath()
        ctx.strokeStyle = color + '80'
        ctx.lineWidth = 2
        const startX = (width / 5) * i + width / 10
        const startY = height / 2 + Math.sin(startX * 0.01 + time) * 30
        
        ctx.moveTo(startX, startY)
        for (let j = 0; j < 50; j++) {
          const x = startX + Math.cos(j * 0.1 + i) * j * 2
          const y = startY + Math.sin(j * 0.1 + time + i) * j * 1.5 - j * 2
          ctx.lineTo(x, y)
        }
        ctx.stroke()
      }
      
      // Draw leaves
      leaves.forEach((leaf, i) => {
        const swayOffset = Math.sin(time * leaf.sway + i) * 5
        ctx.save()
        ctx.translate(leaf.x + swayOffset, leaf.y)
        ctx.rotate(leaf.angle + Math.sin(time * 0.5 + i) * 0.2)
        
        // Leaf shape
        ctx.beginPath()
        ctx.fillStyle = color
        ctx.ellipse(0, 0, leaf.size / 2, leaf.size, 0, 0, Math.PI * 2)
        ctx.fill()
        
        // Leaf vein
        ctx.beginPath()
        ctx.strokeStyle = color + '60'
        ctx.lineWidth = 1
        ctx.moveTo(0, -leaf.size + 3)
        ctx.lineTo(0, leaf.size - 3)
        ctx.stroke()
        
        ctx.restore()
      })
      
      // Draw glow effect
      const gradient = ctx.createRadialGradient(width / 2, height / 2, 0, width / 2, height / 2, width / 2)
      gradient.addColorStop(0, color + '10')
      gradient.addColorStop(1, 'transparent')
      ctx.fillStyle = gradient
      ctx.fillRect(0, 0, width, height)
    }
    
    // Animation loop
    const animate = () => {
      time += 0.016
      drawVine()
      animationRef.current = requestAnimationFrame(animate)
    }
    animate()
    
    return () => {
      window.removeEventListener('resize', resize)
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [leafCount, color])

  return (
    <canvas
      ref={canvasRef}
      style={{
        width: '100%',
        height: '200px',
        borderRadius: '12px',
        background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)'
      }}
    />
  )
}

export default VineCanvas
