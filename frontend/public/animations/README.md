# Digital human animations

## `three-vrm-test.vrma`

- Source: `pixiv/three-vrm`
- Original path: `packages/three-vrm-animation/examples/models/test.vrma`
- Repository: https://github.com/pixiv/three-vrm
- License: MIT
- Purpose: VRMA loader and animation-retargeting verification only. This is a test animation, not a complete production motion set.

The downloaded character model does not include animations. VRoid Hub preview motions are separate assets supplied by its web viewer and are not included here.

## VRoid Project VRMA MotionPack

The seven files under `vrma/` are loaded through `@pixiv/three-vrm-animation` and now control the avatar's full-body pose without Mixamo retargeting or programmatic arm-angle overrides.

The included English and Japanese readme files define the applicable terms. Commercial use requires the credit phrase:

`Animation credits to pixiv Inc.'s VRoid Project`

The files under `fbx/` are retained as user-provided source assets but are no longer loaded by the application.
