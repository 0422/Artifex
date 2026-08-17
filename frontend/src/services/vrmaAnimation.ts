import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import type { VRM } from '@pixiv/three-vrm'
import { createVRMAnimationClip, VRMAnimationLoaderPlugin, type VRMAnimation } from '@pixiv/three-vrm-animation'

const loader = new GLTFLoader()
loader.register((parser) => new VRMAnimationLoaderPlugin(parser))

export async function loadVRMAnimation(url: string, vrm: VRM) {
  const gltf = await loader.loadAsync(url)
  const animations = gltf.userData.vrmAnimations as VRMAnimation[] | undefined
  const animation = animations?.[0]
  if (!animation) throw new Error(`VRMA animation not found: ${url}`)
  return createVRMAnimationClip(animation, vrm)
}
