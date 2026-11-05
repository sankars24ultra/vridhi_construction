import { useEffect, useRef } from 'react'
import * as THREE from 'three'

export default function LoginCity({ darkMode }: { darkMode: boolean }) {
  const container = useRef<HTMLDivElement>(null)
  const trustLabel = useRef<HTMLSpanElement>(null)
  const futureLabel = useRef<HTMLSpanElement>(null)
  useEffect(() => {
    const host = container.current
    if (!host) return
    const scene = new THREE.Scene()
    const palette = darkMode
      ? { ground: '#101217', building: '#71849c', tower: '#285a8e', detail: '#a4bdd8', road: '#3b6088', ambient: '#667c9c' }
      : { ground: '#e5ebf0', building: '#f4f6f8', tower: '#285a8e', detail: '#c5d5e5', road: '#496d94', ambient: '#a5b7cd' }
    scene.background = new THREE.Color(palette.ground)
    const camera = new THREE.OrthographicCamera(-12, 12, 12, -12, .1, 100)
    camera.position.set(18, 17, 22)
    camera.lookAt(0, 3, 0)
    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true })
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2))
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type = THREE.PCFShadowMap
    renderer.outputColorSpace = THREE.SRGBColorSpace
    host.appendChild(renderer.domElement)
    scene.add(new THREE.HemisphereLight('#ffffff', palette.ambient, darkMode ? 1.6 : 2.6))
    const sunlight = new THREE.DirectionalLight('#ffffff', darkMode ? 2 : 3)
    sunlight.position.set(-10, 22, 12)
    sunlight.castShadow = true
    sunlight.shadow.mapSize.set(2048, 2048)
    Object.assign(sunlight.shadow.camera, { left: -15, right: 15, top: 15, bottom: -15 })
    sunlight.shadow.normalBias = .04
    sunlight.shadow.radius = 4
    scene.add(sunlight)
    const city = new THREE.Group()
    scene.add(city)
    const white = new THREE.MeshStandardMaterial({ color: palette.building, roughness: .85 })
    const green = new THREE.MeshStandardMaterial({ color: palette.tower, roughness: .55, metalness: .08 })
    const pale = new THREE.MeshStandardMaterial({ color: palette.detail, roughness: .8 })
    const road = new THREE.MeshStandardMaterial({ color: palette.road, roughness: 1 })
    const box = (width: number, height: number, depth: number, x: number, y: number, z: number, material: THREE.Material) => {
      const mesh = new THREE.Mesh(new THREE.BoxGeometry(width, height, depth), material)
      mesh.position.set(x, y, z)
      mesh.castShadow = true
      mesh.receiveShadow = true
      city.add(mesh)
      return mesh
    }
    box(15, .35, 13, 0, -.2, 0, white)
    box(13.5, .025, .45, 0, .01, 4.6, road)
    box(.45, .025, 10.125, -5.6, .01, -.6875, road)
    box(.4, .025, 10.125, 5.6, .01, -.6875, pale)
    const buildings = [
      [-3.6, -2.6, 2, 1.7, 5.8, 1], [0, -3, 2.2, 2, 8.6, 1], [3.1, -2.5, 1.8, 1.8, 4.8, 0],
      [-4, .2, 1.4, 1.7, 2.6, 0], [-1.4, -.3, 1.7, 1.7, 4.2, 0], [1.2, .1, 1.9, 1.7, 3.7, 1],
      [3.7, .3, 1.6, 1.5, 2.4, 0], [-3.9, 2.8, 1.5, 1.3, 2, 0], [-1.6, 2.5, 1.5, 1.5, 2.8, 0],
      [1, 2.9, 1.7, 1.5, 4.5, 1], [3.7, 2.8, 1.4, 1.6, 2.6, 0], [-.3, -5, 1.5, 1, 2.2, 0],
      [3.4, -4.9, 1.4, 1, 2.8, 0], [-3.7, -4.8, 1.4, 1, 2.1, 0],
    ]
    for (const [x, z, width, depth, height, tower] of buildings) {
      box(width, height, depth, x, height / 2, z, tower ? green : white)
      box(width + .08, .12, depth + .08, x, height + .06, z, white)
      box(width * .75, .24, depth * .75, x, height + .22, z, pale)
      if (tower) {
        for (let floor = .35; floor < height; floor += .32) box(width + .025, .045, depth + .025, x, floor, z, pale)
      } else {
        for (let column = -width / 2 + .24; column < width / 2; column += .38) {
          box(.08, height * .7, .025, x + column, height * .48, z + depth / 2 + .02, pale)
        }
      }
    }
    box(.04, 1.1, .04, 0, 9.4, -3, white)
    for (let index = 0; index < 15; index++) {
      const x = -6.4 + (index % 8) * 1.7
      const z = index < 8 ? 5.5 : -5.7
      const trunk = new THREE.Mesh(new THREE.CylinderGeometry(.025, .035, .5, 10), road)
      trunk.position.set(x, .225, z)
      trunk.castShadow = true
      trunk.receiveShadow = true
      city.add(trunk)
      const foliage = new THREE.Mesh(new THREE.SphereGeometry(.3, 24, 16), pale)
      foliage.position.set(x, .68, z)
      foliage.castShadow = true
      city.add(foliage)
    }
    const ground = new THREE.Mesh(new THREE.PlaneGeometry(200, 200), new THREE.MeshStandardMaterial({ color: palette.ground, roughness: 1 }))
    ground.rotation.x = -Math.PI / 2
    ground.position.y = -.4
    ground.receiveShadow = true
    scene.add(ground)
    const resize = () => {
      const { width, height } = host.getBoundingClientRect()
      if (!width || !height) return
      const aspect = width / height
      const halfHeight = Math.max(9, 11 / aspect)
      camera.left = -halfHeight * aspect
      camera.right = halfHeight * aspect
      camera.top = halfHeight
      camera.bottom = -halfHeight
      camera.updateProjectionMatrix()
      renderer.setSize(width, height)
    }
    const observer = new ResizeObserver(resize)
    observer.observe(host)
    resize()
    let targetRotation = 0
    const pointerMove = (event: PointerEvent) => {
      const bounds = host.getBoundingClientRect()
      targetRotation = ((event.clientX - bounds.left) / bounds.width - .5) * .12
    }
    const pointerLeave = () => { targetRotation = 0 }
    host.addEventListener('pointermove', pointerMove)
    host.addEventListener('pointerleave', pointerLeave)
    renderer.setAnimationLoop(() => {
      city.rotation.y += (targetRotation - city.rotation.y) * .035
      renderer.render(scene, camera)
      for (const [label, anchor, direction] of [
        [trustLabel.current, new THREE.Vector3(4.5, -.65, 7.2), new THREE.Vector3(1, 0, 0)],
        [futureLabel.current, new THREE.Vector3(8.2, -.65, 3.8), new THREE.Vector3(0, 0, -1)],
      ] as const) {
        if (!label) continue
        const endpoint = anchor.clone().add(direction)
        city.localToWorld(endpoint)
        endpoint.project(camera)
        city.localToWorld(anchor)
        anchor.project(camera)
        const bounds = host.getBoundingClientRect()
        const angle = Math.atan2(-(endpoint.y - anchor.y) * bounds.height, (endpoint.x - anchor.x) * bounds.width)
        const halfWidth = (Math.abs(Math.cos(angle)) * label.offsetWidth + Math.abs(Math.sin(angle)) * label.offsetHeight) / 2 + 8
        const halfHeight = (Math.abs(Math.sin(angle)) * label.offsetWidth + Math.abs(Math.cos(angle)) * label.offsetHeight) / 2 + 8
        const left = Math.max(halfWidth, Math.min(bounds.width - halfWidth, (anchor.x + 1) / 2 * bounds.width))
        const top = Math.max(halfHeight, Math.min(bounds.height - halfHeight, (1 - anchor.y) / 2 * bounds.height))
        label.style.left = `${left}px`
        label.style.top = `${top}px`
        label.style.transform = `translate(-50%, -50%) rotate(${angle}rad)`
      }
    })
    return () => {
      observer.disconnect()
      host.removeEventListener('pointermove', pointerMove)
      host.removeEventListener('pointerleave', pointerLeave)
      renderer.setAnimationLoop(null)
      scene.traverse(object => {
        if (object instanceof THREE.Mesh) object.geometry.dispose()
      })
      for (const material of [white, green, pale, road, ground.material]) material.dispose()
      renderer.dispose()
      renderer.domElement.remove()
    }
  }, [darkMode])
  return <div ref={container} className="login-city"><span ref={trustLabel} className="city-side-label">Building trust</span><span ref={futureLabel} className="city-side-label">Creating futures</span></div>
}