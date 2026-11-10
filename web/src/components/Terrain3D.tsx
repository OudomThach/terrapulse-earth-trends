/** Interactive 3D terrain. Orbit with the mouse; click the ground to move the ignition point.
 *  Rendering is on demand (no idle loop), and colours are written straight into a vertex buffer. */

import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { colorize, type FireData, type FireMode } from '../lib/fire'

interface Props {
  data: FireData
  mode: FireMode
  tMin: number
  ignition: { row: number; col: number }
  windDeg: number
  onPick: (row: number, col: number) => void
}

interface SceneCtx {
  render: () => void
  colors: THREE.BufferAttribute
  mesh: THREE.Mesh
  beacon: THREE.Group
  arrow: THREE.ArrowHelper
}

/** Three.js terrain that recolours per frame from precomputed arrival times (no network calls while playing). */
export default function Terrain3D({ data, mode, tMin, ignition, windDeg, onPick }: Props) {
  const host = useRef<HTMLDivElement>(null)
  const ctx = useRef<SceneCtx | null>(null)
  const pick = useRef(onPick)
  pick.current = onPick

  // Build the scene when the terrain changes.
  useEffect(() => {
    const el = host.current
    if (!el) return
    const { rows, cols, cellM, dem, minElev, exaggeration } = data
    const W = (cols - 1) * cellM
    const H = (rows - 1) * cellM

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.outputColorSpace = THREE.LinearSRGBColorSpace // show vertex colours exactly as authored (no extra gamma)
    const sky = new THREE.Color(0.043, 0.051, 0.063) // #0b0d10 expressed in the (linear) output space
    renderer.setClearColor(sky)
    el.appendChild(renderer.domElement)
    const scene = new THREE.Scene()
    scene.fog = new THREE.Fog(sky, W * 1.7, W * 4)
    const camera = new THREE.PerspectiveCamera(40, 1, 10, W * 12)
    camera.position.set(W * 0.5, W * 0.72, W * 0.5)
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.target.set(W / 2, 40, -H / 2)
    controls.maxPolarAngle = Math.PI * 0.49
    controls.minDistance = W * 0.25
    controls.maxDistance = W * 3
    controls.update()

    // terrain mesh: x east, y up, z south (row 0 is the southern edge)
    const positions = new Float32Array(rows * cols * 3)
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const i = r * cols + c
        positions[i * 3] = c * cellM
        positions[i * 3 + 1] = (dem[i]! - minElev) * exaggeration
        positions[i * 3 + 2] = -r * cellM
      }
    }
    const index: number[] = []
    for (let r = 0; r < rows - 1; r++) {
      for (let c = 0; c < cols - 1; c++) {
        const a = r * cols + c, b = a + 1, d = a + cols, e = d + 1
        index.push(a, d, b, b, d, e)
      }
    }
    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    const colors = new THREE.BufferAttribute(new Float32Array(rows * cols * 3), 3)
    geometry.setAttribute('color', colors)
    geometry.setIndex(index)
    geometry.computeBoundingSphere()
    const material = new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide })
    const mesh = new THREE.Mesh(geometry, material)
    scene.add(mesh)

    // ignition beacon and wind arrow
    const beacon = new THREE.Group()
    const ball = new THREE.Mesh(new THREE.SphereGeometry(26, 20, 14), new THREE.MeshBasicMaterial({ color: 0xff3b3b }))
    const mast = new THREE.Mesh(new THREE.CylinderGeometry(3, 3, 200, 8), new THREE.MeshBasicMaterial({ color: 0xff7a7a }))
    mast.position.y = 100
    ball.position.y = 205
    beacon.add(ball, mast)
    scene.add(beacon)
    const arrow = new THREE.ArrowHelper(new THREE.Vector3(1, 0, 0), new THREE.Vector3(), 420, 0x7fd1ff, 120, 70)
    scene.add(arrow)

    const render = () => renderer.render(scene, camera)
    controls.addEventListener('change', render)
    const resize = () => {
      const { clientWidth: w, clientHeight: h } = el
      if (!w || !h) return
      renderer.setSize(w, h)
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      render()
    }
    const observer = new ResizeObserver(resize)
    observer.observe(el)

    // click (not drag) to move the ignition point
    const ray = new THREE.Raycaster()
    let down: { x: number; y: number } | null = null
    const dom = renderer.domElement
    const onDown = (e: PointerEvent) => { down = { x: e.clientX, y: e.clientY } }
    const onUp = (e: PointerEvent) => {
      if (!down || Math.hypot(e.clientX - down.x, e.clientY - down.y) > 5) return
      const rect = dom.getBoundingClientRect()
      ray.setFromCamera(new THREE.Vector2(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1), camera)
      const hit = ray.intersectObject(mesh)[0]
      if (!hit) return
      pick.current(Math.max(0, Math.min(rows - 1, Math.round(-hit.point.z / cellM))), Math.max(0, Math.min(cols - 1, Math.round(hit.point.x / cellM))))
    }
    dom.addEventListener('pointerdown', onDown)
    dom.addEventListener('pointerup', onUp)
    dom.style.cursor = 'crosshair'

    ctx.current = { render, colors, mesh, beacon, arrow }
    resize()
    return () => {
      ctx.current = null
      observer.disconnect()
      dom.removeEventListener('pointerdown', onDown)
      dom.removeEventListener('pointerup', onUp)
      controls.dispose()
      geometry.dispose()
      material.dispose()
      renderer.dispose()
      el.removeChild(dom)
    }
  }, [data.dem, data.rows, data.cols, data.cellM])

  // Colour the terrain for the current time and mode.
  useEffect(() => {
    const c = ctx.current
    if (!c) return
    colorize(c.colors.array as Float32Array, data, mode, tMin)
    c.colors.needsUpdate = true
    c.render()
  }, [data, mode, tMin])

  // Move the ignition beacon and point the wind arrow.
  useEffect(() => {
    const c = ctx.current
    if (!c) return
    const i = ignition.row * data.cols + ignition.col
    const x = ignition.col * data.cellM
    const y = (data.dem[i]! - data.minElev) * data.exaggeration
    const z = -ignition.row * data.cellM
    c.beacon.position.set(x, y, z)
    c.arrow.position.set(x, y + 260, z)
    const rad = (windDeg * Math.PI) / 180
    c.arrow.setDirection(new THREE.Vector3(Math.sin(rad), 0, -Math.cos(rad)))
    c.render()
  }, [data, ignition.row, ignition.col, windDeg])

  return <div ref={host} style={{ width: '100%', height: '100%' }} role="img" aria-label="3D terrain showing the fire" />
}
