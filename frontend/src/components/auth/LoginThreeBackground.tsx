'use client'

import { useEffect, useRef } from 'react'
import * as THREE from 'three'

type LoginThreeBackgroundProps = {
  mode: 'low' | 'high'
}

export function LoginThreeBackground({ mode }: LoginThreeBackgroundProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(55, container.clientWidth / container.clientHeight, 0.1, 1000)
    camera.position.set(0, 0.6, 18)

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setSize(container.clientWidth, container.clientHeight)
    container.appendChild(renderer.domElement)

    const world = new THREE.Group()
    scene.add(world)

    const particleCount = mode === 'high' ? 900 : 420
    const particleGeometry = new THREE.BufferGeometry()
    const positions = new Float32Array(particleCount * 3)
    const basePositions = new Float32Array(particleCount * 3)
    const particleSpeeds = new Float32Array(particleCount)

    const spreadX = mode === 'high' ? 28 : 22
    const spreadY = mode === 'high' ? 14 : 10
    for (let i = 0; i < particleCount; i += 1) {
      const x = (Math.random() - 0.5) * spreadX
      const y = (Math.random() - 0.5) * spreadY
      const z = (Math.random() - 0.5) * 12
      positions[i * 3] = x
      positions[i * 3 + 1] = y
      positions[i * 3 + 2] = z
      basePositions[i * 3] = positions[i * 3]
      basePositions[i * 3 + 1] = positions[i * 3 + 1]
      basePositions[i * 3 + 2] = positions[i * 3 + 2]
      particleSpeeds[i] = 0.25 + Math.random() * 0.8
    }

    particleGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    const particleMaterial = new THREE.PointsMaterial({
      size: mode === 'high' ? 0.1 : 0.085,
      color: '#f97316',
      transparent: true,
      opacity: 0.8,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      sizeAttenuation: true,
    })
    const particles = new THREE.Points(particleGeometry, particleMaterial)
    world.add(particles)

    const energyFlow = new THREE.LineSegments(
      new THREE.EdgesGeometry(new THREE.IcosahedronGeometry(5.8, 1)),
      new THREE.LineBasicMaterial({
        color: '#f43f5e',
        transparent: true,
        opacity: 0.24,
      })
    )
    energyFlow.position.set(0, 0.2, -3)
    world.add(energyFlow)

    const chargerBody = new THREE.Mesh(
      new THREE.BoxGeometry(1.25, 2.4, 0.8),
      new THREE.MeshBasicMaterial({ color: '#38bdf8', transparent: true, opacity: 0.24 })
    )
    chargerBody.position.set(-9.5, -0.9, -1.6)
    world.add(chargerBody)

    const chargerScreen = new THREE.Mesh(
      new THREE.PlaneGeometry(0.72, 0.48),
      new THREE.MeshBasicMaterial({ color: '#e879f9', transparent: true, opacity: 0.45 })
    )
    chargerScreen.position.set(-9.5, -0.35, -1.15)
    world.add(chargerScreen)

    const solarPanel = new THREE.Mesh(
      new THREE.PlaneGeometry(4.8, 2.3, 8, 4),
      new THREE.MeshBasicMaterial({
        color: '#60a5fa',
        transparent: true,
        opacity: 0.22,
        wireframe: true,
      })
    )
    solarPanel.position.set(9.8, -1.9, -2.3)
    solarPanel.rotation.x = -Math.PI / 3.1
    solarPanel.rotation.z = -0.12
    world.add(solarPanel)

    const boltPoints = [
      new THREE.Vector3(0, 3.5, 0),
      new THREE.Vector3(-0.6, 2.1, 0),
      new THREE.Vector3(0.25, 2.1, 0),
      new THREE.Vector3(-0.3, 0.7, 0),
      new THREE.Vector3(0.9, 0.7, 0),
      new THREE.Vector3(0, -1.5, 0),
    ]
    const bolt = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(boltPoints),
      new THREE.LineBasicMaterial({ color: '#facc15', transparent: true, opacity: 0.72 })
    )
    bolt.position.set(7.6, 0.5, -1.5)
    world.add(bolt)

    const carOutlinePoints = [
      new THREE.Vector3(-1.8, -0.2, 0),
      new THREE.Vector3(-1.1, 0.35, 0),
      new THREE.Vector3(0.4, 0.35, 0),
      new THREE.Vector3(1.5, -0.05, 0),
      new THREE.Vector3(1.8, -0.45, 0),
      new THREE.Vector3(-1.8, -0.45, 0),
      new THREE.Vector3(-1.8, -0.2, 0),
    ]
    const carOutline = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(carOutlinePoints),
      new THREE.LineBasicMaterial({ color: '#fb7185', transparent: true, opacity: 0.66 })
    )
    carOutline.position.set(8.3, 1.9, -2.2)
    carOutline.rotation.z = 0.05
    world.add(carOutline)

    const wheelRingGeometry = new THREE.RingGeometry(0.16, 0.28, 32)
    const wheelMaterial = new THREE.MeshBasicMaterial({ color: '#c084fc', transparent: true, opacity: 0.64, side: THREE.DoubleSide })
    const wheelLeft = new THREE.Mesh(wheelRingGeometry, wheelMaterial)
    const wheelRight = new THREE.Mesh(wheelRingGeometry, wheelMaterial.clone())
    wheelLeft.position.set(7.25, 1.45, -2.2)
    wheelRight.position.set(9.35, 1.45, -2.2)
    world.add(wheelLeft)
    world.add(wheelRight)

    const cablePathPoints = [
      new THREE.Vector3(9.2, -1.4, -2.1),
      new THREE.Vector3(5.2, -1.1, -1.9),
      new THREE.Vector3(1.4, -0.5, -1.8),
      new THREE.Vector3(-3.8, -0.7, -1.7),
      new THREE.Vector3(-9.0, -0.8, -1.55),
    ]
    const cableCurve = new THREE.CatmullRomCurve3(cablePathPoints)
    const cableTube = new THREE.Mesh(
      new THREE.TubeGeometry(cableCurve, 120, 0.04, 10, false),
      new THREE.MeshBasicMaterial({ color: '#6366f1', transparent: true, opacity: 0.4 })
    )
    world.add(cableTube)

    const pulseGeometry = new THREE.SphereGeometry(0.11, 12, 12)
    const pulseA = new THREE.Mesh(
      pulseGeometry,
      new THREE.MeshBasicMaterial({ color: '#f59e0b', transparent: true, opacity: 0.95 })
    )
    const pulseB = new THREE.Mesh(
      pulseGeometry,
      new THREE.MeshBasicMaterial({ color: '#22d3ee', transparent: true, opacity: 0.9 })
    )
    world.add(pulseA)
    world.add(pulseB)

    const logoCanvas = document.createElement('canvas')
    logoCanvas.width = 512
    logoCanvas.height = 256
    const logoCtx = logoCanvas.getContext('2d')
    if (logoCtx) {
      logoCtx.clearRect(0, 0, logoCanvas.width, logoCanvas.height)
      logoCtx.fillStyle = 'rgba(6, 182, 212, 0.12)'
      logoCtx.fillRect(0, 0, logoCanvas.width, logoCanvas.height)
      logoCtx.font = '700 58px Arial'
      logoCtx.textAlign = 'center'
      logoCtx.textBaseline = 'middle'
      logoCtx.shadowColor = 'rgba(34, 211, 238, 0.9)'
      logoCtx.shadowBlur = 24
      logoCtx.fillStyle = '#67e8f9'
      logoCtx.fillText('EV POWER', logoCanvas.width / 2, logoCanvas.height / 2)
      logoCtx.strokeStyle = 'rgba(217, 70, 239, 0.8)'
      logoCtx.lineWidth = 3
      logoCtx.strokeText('EV POWER', logoCanvas.width / 2, logoCanvas.height / 2)
    }
    const logoTexture = new THREE.CanvasTexture(logoCanvas)
    const logoPlane = new THREE.Mesh(
      new THREE.PlaneGeometry(5.2, 1.7),
      new THREE.MeshBasicMaterial({
        map: logoTexture,
        transparent: true,
        opacity: 0.68,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      })
    )
    logoPlane.position.set(-7.8, 2.1, -1.2)
    logoPlane.rotation.y = 0.2
    world.add(logoPlane)

    const mouse = { x: 0, y: 0 }
    const onMouseMove = (event: MouseEvent) => {
      const x = (event.clientX / window.innerWidth) * 2 - 1
      const y = (event.clientY / window.innerHeight) * 2 - 1
      mouse.x = x
      mouse.y = y
    }
    window.addEventListener('mousemove', onMouseMove)

    const clock = new THREE.Clock()
    let rafId = 0

    const animate = () => {
      const elapsed = clock.getElapsedTime()
      const pos = particleGeometry.getAttribute('position') as THREE.BufferAttribute

      for (let i = 0; i < particleCount; i += 1) {
        const idx = i * 3
        const speed = particleSpeeds[i]
        pos.array[idx] = basePositions[idx] + Math.sin(elapsed * speed + i * 0.4) * 0.35
        pos.array[idx + 1] = basePositions[idx + 1] + Math.cos(elapsed * speed * 1.2 + i * 0.3) * 0.45
        pos.array[idx + 2] = basePositions[idx + 2] + Math.sin(elapsed * speed * 0.7 + i * 0.2) * 0.2
      }
      pos.needsUpdate = true

      world.rotation.y = elapsed * 0.08 + mouse.x * 0.2
      world.rotation.x = -0.06 + mouse.y * 0.14
      world.position.y = Math.sin(elapsed * 0.7) * 0.18

      energyFlow.rotation.y = -elapsed * 0.3
      energyFlow.material.opacity = 0.18 + Math.abs(Math.sin(elapsed * 1.6)) * 0.24
      bolt.material.opacity = 0.45 + Math.abs(Math.sin(elapsed * 4.2)) * 0.35
      chargerScreen.material.opacity = 0.24 + Math.abs(Math.sin(elapsed * 1.8)) * 0.36
      logoPlane.material.opacity = 0.45 + Math.abs(Math.sin(elapsed * 1.5)) * 0.28
      logoPlane.position.y = 2.1 + Math.sin(elapsed * 1.2) * 0.14

      const tA = (elapsed * 0.26) % 1
      const tB = ((elapsed * 0.26) + 0.42) % 1
      pulseA.position.copy(cableCurve.getPointAt(tA))
      pulseB.position.copy(cableCurve.getPointAt(tB))
      pulseA.scale.setScalar(1 + Math.abs(Math.sin(elapsed * 4)) * 0.5)
      pulseB.scale.setScalar(1 + Math.abs(Math.cos(elapsed * 3.6)) * 0.45)

      camera.position.x += ((mouse.x * 1.6) - camera.position.x) * 0.05
      camera.position.y += ((0.6 - mouse.y * 1.2) - camera.position.y) * 0.05
      camera.lookAt(scene.position)

      renderer.render(scene, camera)
      rafId = window.requestAnimationFrame(animate)
    }
    animate()

    const onResize = () => {
      if (!container) return
      camera.aspect = container.clientWidth / container.clientHeight
      camera.updateProjectionMatrix()
      renderer.setSize(container.clientWidth, container.clientHeight)
    }
    window.addEventListener('resize', onResize)

    return () => {
      window.cancelAnimationFrame(rafId)
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('resize', onResize)
      particleGeometry.dispose()
      particleMaterial.dispose()
      ;(energyFlow.geometry as THREE.BufferGeometry).dispose()
      ;(energyFlow.material as THREE.Material).dispose()
      chargerBody.geometry.dispose()
      ;(chargerBody.material as THREE.Material).dispose()
      chargerScreen.geometry.dispose()
      ;(chargerScreen.material as THREE.Material).dispose()
      solarPanel.geometry.dispose()
      ;(solarPanel.material as THREE.Material).dispose()
      ;(bolt.geometry as THREE.BufferGeometry).dispose()
      ;(bolt.material as THREE.Material).dispose()
      ;(carOutline.geometry as THREE.BufferGeometry).dispose()
      ;(carOutline.material as THREE.Material).dispose()
      wheelRingGeometry.dispose()
      wheelMaterial.dispose()
      ;(wheelRight.material as THREE.Material).dispose()
      ;(cableTube.geometry as THREE.BufferGeometry).dispose()
      ;(cableTube.material as THREE.Material).dispose()
      pulseGeometry.dispose()
      ;(pulseA.material as THREE.Material).dispose()
      ;(pulseB.material as THREE.Material).dispose()
      logoTexture.dispose()
      logoPlane.geometry.dispose()
      ;(logoPlane.material as THREE.Material).dispose()
      renderer.dispose()
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement)
      }
    }
  }, [mode])

  return <div ref={containerRef} className="ai-three-layer" aria-hidden="true" />
}
