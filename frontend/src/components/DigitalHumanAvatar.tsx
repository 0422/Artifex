import { useEffect, useRef, useState } from 'react'
import { RotateCcw, Upload, UserRound } from 'lucide-react'
import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { VRM, VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm'
import { loadVRMAnimation } from '../services/vrmaAnimation'

export type DigitalHumanMood = 'neutral' | 'happy' | 'thinking' | 'relaxed' | 'sad'
export type DigitalHumanMotion = 'auto' | 'showcase' | 'greeting' | 'peace' | 'shoot' | 'spin' | 'modelPose' | 'squat'

interface DigitalHumanAvatarProps {
  mood: DigitalHumanMood
  isSpeaking: boolean
  mouthLevel: number
  motion: DigitalHumanMotion
  viewScale: number
  onViewScaleChange?: (scale: number) => void
  viewRotation: number
  onViewRotationChange?: (rotation: number) => void
  defaultModelUrl?: string
}

const MOOD_EXPRESSION: Record<DigitalHumanMood, string | null> = {
  neutral: 'neutral',
  happy: 'happy',
  thinking: 'relaxed',
  relaxed: 'relaxed',
  sad: 'sad',
}

export default function DigitalHumanAvatar({
  mood,
  isSpeaking,
  mouthLevel,
  motion,
  viewScale,
  onViewScaleChange,
  viewRotation,
  onViewRotationChange,
  defaultModelUrl = '/models/free.vrm',
}: DigitalHumanAvatarProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const objectUrlRef = useRef<string | null>(null)
  const moodRef = useRef(mood)
  const speakingRef = useRef(isSpeaking)
  const mouthLevelRef = useRef(mouthLevel)
  const motionRef = useRef(motion)
  const viewScaleRef = useRef(viewScale)
  const viewRotationRef = useRef(viewRotation)
  const rotatingRef = useRef(false)
  const previousPointerXRef = useRef(0)
  const [modelUrl, setModelUrl] = useState(defaultModelUrl)
  const [loadState, setLoadState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [usingCustomModel, setUsingCustomModel] = useState(false)
  const [isRotating, setIsRotating] = useState(false)

  useEffect(() => { moodRef.current = mood }, [mood])
  useEffect(() => { speakingRef.current = isSpeaking }, [isSpeaking])
  useEffect(() => { mouthLevelRef.current = mouthLevel }, [mouthLevel])
  useEffect(() => { motionRef.current = motion }, [motion])
  useEffect(() => { viewScaleRef.current = viewScale }, [viewScale])
  useEffect(() => { viewRotationRef.current = viewRotation }, [viewRotation])

  useEffect(() => {
    const canvas = canvasRef.current
    const container = containerRef.current
    if (!canvas || !container) return

    let disposed = false
    let animationFrame = 0
    let currentVrm: VRM | null = null
    let mixer: THREE.AnimationMixer | null = null
    let activeAction: THREE.AnimationAction | null = null
    let activeMotion = ''
    const motionClips = new Map<string, THREE.AnimationClip>()
    let nextBlinkAt = 1.5 + Math.random() * 2
    let blinkStartedAt: number | null = null
    let renderedMouth = 0
    let modelHeight = 1
    let cameraTargetY = 0.5
    let baseModelRotationY = 0
    let pageVisible = !document.hidden
    let inViewport = true

    setLoadState('loading')
    let renderer: THREE.WebGLRenderer
    try {
      renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true, powerPreference: 'high-performance' })
    } catch {
      queueMicrotask(() => {
        if (!disposed) setLoadState('error')
      })
      return () => { disposed = true }
    }
    renderer.outputColorSpace = THREE.SRGBColorSpace
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(28, 1, 0.01, 100)
    camera.position.set(0, 1.35, 2.7)

    const hemisphere = new THREE.HemisphereLight(0xf4f4f5, 0x18181b, 2.5)
    scene.add(hemisphere)
    const keyLight = new THREE.DirectionalLight(0xffffff, 3.2)
    keyLight.position.set(1.5, 2.8, 2.5)
    scene.add(keyLight)
    const rimLight = new THREE.DirectionalLight(0x5eead4, 2.2)
    rimLight.position.set(-2, 1.8, -1)
    scene.add(rimLight)

    const loader = new GLTFLoader()
    loader.register((parser) => new VRMLoaderPlugin(parser))
    loader.load(
      modelUrl,
      (gltf) => {
        if (disposed) return
        const vrm = gltf.userData.vrm as VRM | undefined
        if (!vrm) {
          setLoadState('error')
          return
        }

        VRMUtils.removeUnnecessaryVertices(vrm.scene)
        VRMUtils.removeUnnecessaryJoints(vrm.scene)
        VRMUtils.rotateVRM0(vrm)
        baseModelRotationY = vrm.scene.rotation.y
        currentVrm = vrm
        scene.add(vrm.scene)

        const bounds = new THREE.Box3().setFromObject(vrm.scene)
        const size = bounds.getSize(new THREE.Vector3())
        const center = bounds.getCenter(new THREE.Vector3())
        const height = Math.max(size.y, 1)
        modelHeight = height
        vrm.scene.position.x -= center.x
        vrm.scene.position.y -= bounds.min.y
        vrm.scene.position.z -= center.z

        cameraTargetY = height * 0.5
        camera.position.set(0, cameraTargetY, height * 1.2 / viewScaleRef.current)
        camera.lookAt(0, cameraTargetY, 0)
        camera.near = Math.max(height * 0.01, 0.01)
        camera.far = height * 20
        camera.updateProjectionMatrix()

        setLoadState('ready')

        mixer = new THREE.AnimationMixer(vrm.scene)
        const motionUrls = {
          showcase: '/animations/vrma/VRMA_01.vrma',
          greeting: '/animations/vrma/VRMA_02.vrma',
          peace: '/animations/vrma/VRMA_03.vrma',
          shoot: '/animations/vrma/VRMA_04.vrma',
          spin: '/animations/vrma/VRMA_05.vrma',
          modelPose: '/animations/vrma/VRMA_06.vrma',
          squat: '/animations/vrma/VRMA_07.vrma',
        }
        void Promise.all(Object.entries(motionUrls).map(async ([name, url]) => {
          const clip = await loadVRMAnimation(url, vrm)
          if (!disposed) motionClips.set(name, clip)
        })).catch(() => undefined)
      },
      undefined,
      () => {
        if (!disposed) setLoadState('error')
      },
    )

    const resize = () => {
      const width = Math.max(container.clientWidth, 1)
      const height = Math.max(container.clientHeight, 1)
      renderer.setSize(width, height, false)
      camera.aspect = width / height
      camera.updateProjectionMatrix()
    }
    const resizeObserver = new ResizeObserver(resize)
    resizeObserver.observe(container)
    resize()

    const clock = new THREE.Clock()
    const shouldRender = () => pageVisible && inViewport
    const scheduleFrame = () => {
      if (disposed || !shouldRender() || animationFrame) return
      clock.getDelta()
      animationFrame = window.requestAnimationFrame(animate)
    }
    const animate = () => {
      animationFrame = 0
      if (!shouldRender()) return
      const delta = Math.min(clock.getDelta(), 0.05)
      const elapsed = clock.elapsedTime

      if (currentVrm) {
        const cameraDistance = modelHeight * 1.2 / viewScaleRef.current
        camera.position.z = THREE.MathUtils.lerp(camera.position.z, cameraDistance, Math.min(delta * 10, 1))
        camera.lookAt(0, cameraTargetY, 0)

        const requestedMotion = motionRef.current === 'auto'
          ? speakingRef.current ? 'showcase' : moodRef.current === 'happy' ? 'greeting' : 'modelPose'
          : motionRef.current
        if (requestedMotion !== activeMotion) {
          const nextClip = motionClips.get(requestedMotion)
          if (!requestedMotion || nextClip) {
            activeAction?.fadeOut(0.35)
            activeAction = nextClip && mixer ? mixer.clipAction(nextClip) : null
            activeAction?.reset().setLoop(THREE.LoopRepeat, Infinity).fadeIn(0.35).play()
            activeMotion = requestedMotion
          }
        }
        mixer?.update(delta)
        currentVrm.scene.rotation.y = baseModelRotationY + viewRotationRef.current
        const expressions = currentVrm.expressionManager
        const activeMood = MOOD_EXPRESSION[moodRef.current]
        for (const expression of ['neutral', 'happy', 'relaxed', 'sad']) {
          let target = expression === activeMood ? moodRef.current === 'thinking' ? 0.35 : 0.75 : 0
          if (speakingRef.current) target = Math.min(target, 0.4)
          const current = expressions?.getValue(expression) ?? 0
          expressions?.setValue(expression, THREE.MathUtils.lerp(current, target, delta * 5))
        }

        if (blinkStartedAt === null && elapsed >= nextBlinkAt) blinkStartedAt = elapsed
        let blink = 0
        if (blinkStartedAt !== null) {
          const blinkProgress = (elapsed - blinkStartedAt) / 0.18
          blink = blinkProgress < 1 ? Math.sin(blinkProgress * Math.PI) : 0
          if (blinkProgress >= 1) {
            blinkStartedAt = null
            nextBlinkAt = elapsed + 2.5 + Math.random() * 3
          }
        }
        expressions?.setValue('blink', blink)

        const mouthTarget = speakingRef.current ? Math.max(0.04, mouthLevelRef.current) : 0
        renderedMouth += (mouthTarget - renderedMouth) * (mouthTarget > renderedMouth ? 0.62 : 0.3)
        expressions?.setValue('aa', Math.min(renderedMouth, 1))
        expressions?.setValue('oh', speakingRef.current ? renderedMouth * Math.abs(Math.sin(elapsed * 5.5)) * 0.16 : 0)

        currentVrm.update(delta)
      }

      renderer.render(scene, camera)
      animationFrame = window.requestAnimationFrame(animate)
    }
    const onVisibilityChange = () => {
      pageVisible = !document.hidden
      if (!pageVisible && animationFrame) {
        window.cancelAnimationFrame(animationFrame)
        animationFrame = 0
      } else scheduleFrame()
    }
    const intersectionObserver = new IntersectionObserver(([entry]) => {
      inViewport = entry?.isIntersecting ?? true
      if (!inViewport && animationFrame) {
        window.cancelAnimationFrame(animationFrame)
        animationFrame = 0
      } else scheduleFrame()
    }, { threshold: 0.01 })
    intersectionObserver.observe(container)
    document.addEventListener('visibilitychange', onVisibilityChange)
    scheduleFrame()

    return () => {
      disposed = true
      window.cancelAnimationFrame(animationFrame)
      resizeObserver.disconnect()
      intersectionObserver.disconnect()
      document.removeEventListener('visibilitychange', onVisibilityChange)
      if (currentVrm) {
        scene.remove(currentVrm.scene)
        VRMUtils.deepDispose(currentVrm.scene)
      }
      renderer.dispose()
    }
  }, [modelUrl])

  useEffect(() => () => {
    if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current)
  }, [])

  const selectModel = (file: File | undefined) => {
    if (!file) return
    if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current)
    const objectUrl = URL.createObjectURL(file)
    objectUrlRef.current = objectUrl
    setUsingCustomModel(true)
    setModelUrl(objectUrl)
  }

  const resetModel = () => {
    if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current)
    objectUrlRef.current = null
    setUsingCustomModel(false)
    setModelUrl(defaultModelUrl)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  return (
    <div
      ref={containerRef}
      data-avatar-state={loadState}
      className="relative h-full min-h-80 w-full overflow-hidden bg-zinc-950"
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => {
        event.preventDefault()
        selectModel(event.dataTransfer.files[0])
      }}
      onWheel={(event) => {
        if (!onViewScaleChange) return
        event.preventDefault()
        onViewScaleChange(viewScale - event.deltaY * 0.0006)
      }}
    >
      <canvas
        ref={canvasRef}
        className={`absolute inset-0 h-full w-full touch-none ${isRotating ? 'cursor-grabbing' : 'cursor-grab'}`}
        aria-label="3D 对话伙伴"
        title="拖动旋转，滚轮缩放"
        onPointerDown={(event) => {
          if (event.button !== 0) return
          event.currentTarget.setPointerCapture(event.pointerId)
          rotatingRef.current = true
          previousPointerXRef.current = event.clientX
          setIsRotating(true)
        }}
        onPointerMove={(event) => {
          if (!rotatingRef.current || !event.currentTarget.hasPointerCapture(event.pointerId)) return
          const next = viewRotationRef.current + (event.clientX - previousPointerXRef.current) * 0.012
          previousPointerXRef.current = event.clientX
          viewRotationRef.current = next
          onViewRotationChange?.(next)
        }}
        onPointerUp={(event) => {
          if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
          rotatingRef.current = false
          setIsRotating(false)
        }}
        onPointerCancel={() => {
          rotatingRef.current = false
          setIsRotating(false)
        }}
      />
      <div className="absolute right-3 top-3 z-10 flex gap-1">
        {usingCustomModel && (
          <button type="button" title="恢复默认模型" aria-label="恢复默认模型" onClick={resetModel} className="icon-button bg-zinc-950/80 backdrop-blur-sm">
            <RotateCcw size={16} />
          </button>
        )}
        <button type="button" title="选择 VRM 模型" aria-label="选择 VRM 模型" onClick={() => fileInputRef.current?.click()} className="icon-button bg-zinc-950/80 backdrop-blur-sm">
          <Upload size={16} />
        </button>
        <input ref={fileInputRef} type="file" accept=".vrm,model/gltf-binary" className="hidden" onChange={(event) => selectModel(event.target.files?.[0])} />
      </div>
      {loadState === 'loading' && <div className="absolute inset-0 flex items-center justify-center text-sm text-zinc-500"><span className="h-2 w-2 animate-pulse rounded-full bg-teal-400" /></div>}
      {loadState === 'error' && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-zinc-500">
          <UserRound size={88} strokeWidth={1.1} />
          <span className="text-xs">模型加载失败</span>
        </div>
      )}
    </div>
  )
}
